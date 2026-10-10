"""Independent end scoring: explicit missing outputs and separate position/identity errors."""

import math
import numpy as np
from scipy.optimize import linear_sum_assignment


def unique(rows, label):
    ids = [r["id"] for r in rows]
    if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError(f"Invalid or duplicate {label} IDs")


def interval(value):
    if (
        len(value) != 2
        or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in value)
        or value[0] >= value[1]
    ):
        raise ValueError("Invalid interval")
    return value


def validate_reference(ref):
    if ref.get("purpose") == "practice_only":
        raise ValueError("Practice labels cannot be sealed as independent evaluation")
    if ref.get("schema") != 1 or not ref.get("reviewer") or ref.get("independent") is not True:
        raise ValueError("Named independent reviewer and schema 1 required")
    if ref.get("complete_end_reviewed") is not True:
        raise ValueError("Reviewer must confirm the entire selected end was checked for deliveries")
    lo, hi = interval(ref["source_interval_s"])
    if not ref["events"]:
        raise ValueError("An empty reference is not a labelled end")
    unique(ref["events"], "event")
    unique(ref["boards"], "board")
    last = lo
    for e in sorted(ref["events"], key=lambda e: e["delivery_interval_s"][0]):
        a, b = interval(e["delivery_interval_s"])
        if a < last or b > hi or e["colour"] not in ("red", "yellow"):
            raise ValueError("Overlapping/out-of-range delivery or invalid colour")
        last = b
    event_ids = {e["id"] for e in ref["events"]}
    board_throws = set()
    for b in ref["boards"]:
        if b["throw_id"] not in event_ids or b["throw_id"] in board_throws:
            raise ValueError("Each board must refer to a distinct labelled throw")
        board_throws.add(b["throw_id"])
        if not isinstance(b["complete"], bool) or not lo <= b["time_s"] <= hi:
            raise ValueError("Invalid board completeness or time")
        validate_board(b)
    if board_throws != event_ids:
        raise ValueError("Every throw needs a board record, even if unobservable/incomplete")


def validate_board(board):
    if board["units"] not in ("px", "m") or not board["coordinate_frame"]:
        raise ValueError("Explicit coordinate frame and units required")
    known = []
    for s in board["stones"]:
        p = s["position"]
        if (
            len(p) != 2
            or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in p)
            or s["colour"] not in ("red", "yellow")
        ):
            raise ValueError("Invalid stone position/colour")
        if s.get("identity") is not None:
            known.append(s["identity"])
    if len(set(known)) != len(known):
        raise ValueError("Duplicate stone identity")


def identity_correspondence(pred):
    """Return only explicitly reviewed camera-track to reference-ID links."""
    record = pred.get("identity_correspondence")
    if record is None:
        return {}, "not_supplied"
    if not isinstance(record, dict) or record.get("method") != "reviewed_source_link":
        raise ValueError("Identity correspondence requires reviewed_source_link method")
    mapping = record.get("prediction_to_reference")
    if (
        not isinstance(mapping, dict)
        or any(
            not isinstance(key, str) or not key or not isinstance(value, str) or not value
            for key, value in mapping.items()
        )
        or len(set(mapping.values())) != len(mapping)
    ):
        raise ValueError("Identity correspondence must be a one-to-one string mapping")
    return mapping, record["method"]


def assign(cost, valid):
    """Maximum-cardinality valid matching, then minimum total distance."""
    n, m = cost.shape
    if not n or not m:
        return []
    scale = max(float(np.max(cost[valid])) if valid.any() else 0, 1)
    penalty = scale * (min(n, m) + 1)
    matrix = np.full((n, m + n), penalty)
    matrix[:, :m] = np.where(valid, cost, penalty * (n + m + 2))
    ii, jj = linear_sum_assignment(matrix)
    return [(int(i), int(j)) for i, j in zip(ii, jj) if j < m and valid[i, j]]


def score_board(ref, pred, identity_mapping=None):
    identity_mapping = identity_mapping or {}
    threshold = {"px": 5.0, "m": 0.10}[ref["units"]]
    base = dict(
        id=ref["id"],
        reference_method=ref["reference_method"],
        units=ref["units"],
        tolerance=threshold,
    )
    if pred is None:
        visible = len(ref["stones"])
        if not ref["complete"]:
            return dict(
                base,
                status="reference_incomplete",
                correct=None,
                visible_reference_count=visible,
                visible_reference_matches=0,
                visible_reference_misses=visible,
                visible_reference_recall=0.0 if visible else None,
                visible_identity_errors=0,
                visible_identity_abstentions=0,
                matched_position_errors=[],
                matched_position_rmse=None,
            )
        return dict(
            base,
            status="prediction_missing",
            correct=False,
            misses=visible,
            extras=0,
            visible_reference_count=visible,
            visible_reference_matches=0,
            visible_reference_misses=visible,
            visible_reference_recall=0.0 if visible else None,
            visible_identity_errors=0,
            visible_identity_abstentions=0,
            matched_position_errors=[],
            matched_position_rmse=None,
        )
    validate_board(pred)
    if pred["coordinate_frame"] != ref["coordinate_frame"] or pred["units"] != ref["units"]:
        raise ValueError("Cannot compare different coordinate frames/units")
    if pred["throw_id"] != ref["throw_id"] or abs(pred["time_s"] - ref["time_s"]) > 1e-6:
        raise ValueError("Board prediction must use the fixed reference throw and timestamp")
    if not isinstance(pred.get("complete"), bool):
        raise ValueError("Prediction completeness must be explicit")
    a, b = ref["stones"], pred["stones"]
    cost = np.array(
        [[math.dist(x["position"], y["position"]) for y in b] for x in a], dtype=float
    ).reshape(len(a), len(b))
    valid = np.array([[x["colour"] == y["colour"] for y in b] for x in a], dtype=bool).reshape(
        cost.shape
    ) & (cost <= threshold)
    pairs = assign(cost, valid)
    wrong = sum(
        a[i].get("identity") is not None
        and b[j].get("identity") in identity_mapping
        and a[i]["identity"] != identity_mapping[b[j]["identity"]]
        for i, j in pairs
    )
    unknown = sum(
        a[i].get("identity") is not None and b[j].get("identity") not in identity_mapping
        for i, j in pairs
    )
    positions = [float(cost[i, j]) for i, j in pairs]
    visible = len(a)
    common = dict(
        visible_reference_count=visible,
        visible_reference_matches=len(pairs),
        visible_reference_misses=visible - len(pairs),
        visible_reference_recall=len(pairs) / visible if visible else None,
        visible_identity_errors=wrong,
        visible_identity_abstentions=unknown,
        matched_position_errors=positions,
        matched_position_rmse=math.sqrt(sum(x * x for x in positions) / len(positions))
        if positions
        else None,
    )
    if not ref["complete"]:
        # Unobserved stones make false-positive and complete-board claims impossible.
        return dict(base, status="reference_incomplete", correct=None, **common)
    return dict(
        base,
        status="scored",
        correct=pred["complete"] and len(pairs) == len(a) == len(b) and wrong == 0 and unknown == 0,
        misses=len(a) - len(pairs),
        extras=len(b) - len(pairs),
        identity_errors=wrong,
        identity_abstentions=unknown,
        **common,
    )


def evaluate_end(ref, pred):
    validate_reference(ref)
    if not ref.get("source_sha256") or pred.get("source_sha256") != ref["source_sha256"]:
        raise ValueError("Source hashes must match")
    if pred.get("source_interval_s") != ref["source_interval_s"]:
        raise ValueError("Scored source intervals must match")
    unique(pred["events"], "prediction event")
    unique(pred["boards"], "prediction board")
    identity_mapping, correspondence_method = identity_correspondence(pred)
    lo, hi = ref["source_interval_s"]
    for e in pred["events"]:
        t = e["crossing_time_s"]
        if (
            not isinstance(t, (int, float))
            or not math.isfinite(t)
            or not lo <= t <= hi
            or e["colour"] not in ("red", "yellow")
        ):
            raise ValueError("Invalid predicted event")
    rr, pp = ref["events"], pred["events"]
    valid = np.array(
        [
            [
                r["delivery_interval_s"][0] <= p["crossing_time_s"] <= r["delivery_interval_s"][1]
                for p in pp
            ]
            for r in rr
        ],
        dtype=bool,
    ).reshape(len(rr), len(pp))
    # Interval membership, not proximity to release; deterministic order for ties.
    pairs = assign(np.zeros(valid.shape), valid)
    mi, mj = {i for i, j in pairs}, {j for i, j in pairs}
    known = [(i, j) for i, j in pairs if rr[i].get("arrival_identity") is not None]
    identity_checked = [
        (i, j) for i, j in known if pp[j].get("arrival_identity") in identity_mapping
    ]
    known_total = sum(r.get("arrival_identity") is not None for r in rr)
    matches, misses, extras = len(pairs), len(rr) - len(pairs), len(pp) - len(pairs)
    colour_errors = sum(rr[i]["colour"] != pp[j]["colour"] for i, j in pairs)
    event_precision = matches / len(pp) if pp else 0.0
    event_recall = matches / len(rr)
    event_f1 = (
        2 * matches / (2 * matches + misses + extras) if matches or misses or extras else None
    )
    colour_tp = matches - colour_errors
    colour_precision = colour_tp / len(pp) if pp else 0.0
    colour_recall = colour_tp / len(rr)
    colour_f1 = (
        2 * colour_tp / (2 * colour_tp + misses + extras + 2 * colour_errors)
        if colour_tp or misses or extras or colour_errors
        else None
    )
    boards = {b["id"]: b for b in pred["boards"]}
    unexpected = sorted(set(boards) - {b["id"] for b in ref["boards"]})
    if unexpected:
        raise ValueError(f"Unexpected board IDs: {unexpected}")
    scored = [score_board(b, boards.get(b["id"]), identity_mapping) for b in ref["boards"]]
    eligible = [b for b in scored if b["correct"] is not None]
    complete = sum(b["correct"] for b in eligible)
    visible_total = sum(b["visible_reference_count"] for b in scored)
    visible_matched = sum(b["visible_reference_matches"] for b in scored)
    return {
        "status": "scored_against_human_reference",
        "events": {
            "references": len(rr),
            "predictions": len(pp),
            "matches": matches,
            "misses": misses,
            "extras": extras,
            "missed_ids": [r["id"] for i, r in enumerate(rr) if i not in mi],
            "extra_ids": [p["id"] for j, p in enumerate(pp) if j not in mj],
            "precision": event_precision,
            "recall": event_recall,
            "f1": event_f1,
            "colour_errors": colour_errors,
            "colour_aware_precision": colour_precision,
            "colour_aware_recall": colour_recall,
            "colour_aware_f1": colour_f1,
            "metric_scope": "one_complete_reviewer_declared_end_broad_delivery_intervals",
        },
        "cross_view_identity": {
            "correspondence_method": correspondence_method,
            "known_references": known_total,
            "assessed_predictions": len(identity_checked),
            "correct": sum(
                rr[i]["arrival_identity"] == identity_mapping[pp[j]["arrival_identity"]]
                for i, j in identity_checked
            ),
            "coverage": len(identity_checked) / known_total if known_total else None,
        },
        "boards": {
            "scorable": len(eligible),
            "reference_incomplete": len(scored) - len(eligible),
            "predictions_supplied": sum(b["status"] == "scored" for b in eligible),
            "complete_correct": complete,
            "complete_correct_fraction": complete / len(eligible) if eligible else None,
            "visible_stones": {
                "reference_count": visible_total,
                "matched": visible_matched,
                "missed": visible_total - visible_matched,
                "recall": visible_matched / visible_total if visible_total else None,
                "scope": "annotated_visible_stones_only; no precision or completeness claim for incomplete boards",
            },
            "details": scored,
        },
        "annotation_minutes": ref.get("annotation_minutes"),
        "prediction_effort": pred.get("manual_effort", None),
        "limitations": [
            "One end; no generalization guarantee.",
            "Exhaustive review and independence are reviewer declarations, not facts established by the scorer.",
            "Position errors are conditional on matched detections; misses/extras are reported separately.",
            "Visible-stone recall includes incomplete boards, but their unobserved stones prevent precision or full-state scoring.",
            "Pixel agreement and shared-projection metric agreement are not independent physical accuracy.",
            "Identity correctness requires explicit reviewed prediction-to-reference correspondence; unmapped IDs abstain.",
            "No release timing or unobserved trajectory inferred.",
        ],
    }
