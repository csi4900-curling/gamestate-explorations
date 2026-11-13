"""One-to-one throw-event scoring for frozen, interval-valued references.

Scoring does not infer an end from the expected throw count or the alternating
colour pattern. Unmatched predictions remain false positives even when they are
close to another prediction. Unmatched reference events remain misses.
"""

from __future__ import annotations

import math
from scipy.optimize import linear_sum_assignment


def _interval(value):
    if (
        not isinstance(value, (list, tuple))
        or len(value) != 2
        or any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
            for v in value
        )
        or value[0] >= value[1]
    ):
        raise ValueError(f"Invalid interval: {value!r}")
    return tuple(float(v) for v in value)


def evaluate_events(
    predictions,
    references,
    interval,
    *,
    tolerance_s=0.0,
    prediction_time_mode="point",
    max_prediction_interval_s=None,
    evaluate_colour=True,
):
    """Match a proposed crossing inside a labelled delivery interval, once only.

    Broad delivery intervals establish detection, not release-time accuracy. A
    nonzero tolerance must be declared before predictions are inspected.
    """
    lo, hi = _interval(interval)
    if not math.isfinite(tolerance_s) or tolerance_s < 0:
        raise ValueError("Invalid tolerance")
    if prediction_time_mode not in ("point", "evidence_interval"):
        raise ValueError("Invalid prediction time mode")
    if prediction_time_mode == "evidence_interval" and (
        max_prediction_interval_s is None
        or not math.isfinite(max_prediction_interval_s)
        or max_prediction_interval_s <= 0
    ):
        raise ValueError("Evidence-interval mode requires a finite positive maximum width")
    ref_ids = [r["id"] for r in references]
    pred_ids = [p["id"] for p in predictions]
    if len(set(ref_ids)) != len(ref_ids) or len(set(pred_ids)) != len(pred_ids):
        raise ValueError("Duplicate event IDs")
    ref_windows = []
    for r in references:
        a, b = _interval(r["delivery_interval_s"])
        if a < lo or b > hi or (evaluate_colour and r.get("colour") not in ("red", "yellow")):
            raise ValueError("Invalid reference event")
        ref_windows.append((a, b))
    if any(a[1] > b[0] for a, b in zip(sorted(ref_windows), sorted(ref_windows)[1:])):
        raise ValueError("Overlapping reference intervals")
    pred_windows = []
    for p in predictions:
        t = p["crossing_time_s"]
        if (
            isinstance(t, bool)
            or not isinstance(t, (int, float))
            or not math.isfinite(t)
            or not lo <= t <= hi
            or (evaluate_colour and p.get("colour") not in ("red", "yellow"))
        ):
            raise ValueError("Invalid predicted event")
        if prediction_time_mode == "evidence_interval":
            a, b = _interval(p["evidence_interval_s"])
            if a < lo or b > hi or b - a > max_prediction_interval_s or not a <= t <= b:
                raise ValueError("Invalid or overwide prediction evidence interval")
            pred_windows.append((a, b))
        else:
            pred_windows.append((t, t))
    n, m = len(references), len(predictions)
    # Each valid match costs less than leaving a reference unmatched; this
    # maximizes match count first, then minimizes distance from its interval.
    penalty = max(1.0, tolerance_s + 1.0)
    costs = [[penalty * (n + m + 2)] * m + [penalty] * n for _ in range(n)]
    valid = [[False] * m for _ in range(n)]
    for i, (a, b) in enumerate(ref_windows):
        for j, (c, d) in enumerate(pred_windows):
            distance = max(a - d, c - b, 0.0)
            if distance <= tolerance_s:
                valid[i][j] = True
                costs[i][j] = distance
    pairs = []
    if n:
        rows, columns = linear_sum_assignment(costs)
        pairs = [(int(i), int(j)) for i, j in zip(rows, columns) if j < m and valid[i][j]]
    used_ref = {i for i, _ in pairs}
    used_pred = {j for _, j in pairs}
    tp = len(pairs)
    colour_errors = sum(references[i]["colour"] != predictions[j]["colour"] for i, j in pairs) if evaluate_colour else None
    colour_costs = [row.copy() for row in costs]
    for i in range(n):
        for j in range(m):
            if evaluate_colour and references[i]["colour"] != predictions[j]["colour"]:
                colour_costs[i][j] = penalty * (n + m + 2)
    if n and evaluate_colour:
        colour_rows, colour_columns = linear_sum_assignment(colour_costs)
        colour_pairs = [
            (int(i), int(j))
            for i, j in zip(colour_rows, colour_columns)
            if j < m and valid[i][j] and references[i]["colour"] == predictions[j]["colour"]
        ]
    else:
        colour_pairs = []
    colour_tp = len(colour_pairs)
    precision = tp / m if m else (1.0 if n == 0 else 0.0)
    recall = tp / n if n else (1.0 if m == 0 else 0.0)
    f1 = 2 * tp / (n + m) if n + m else 1.0
    result = {
        "reference_count": n,
        "prediction_count": m,
        "true_positives": tp,
        "false_positives": m - tp,
        "false_negatives": n - tp,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "colour_errors_among_matches": colour_errors,
        "colour_aware_true_positives": colour_tp,
        "colour_aware_false_positives": m - colour_tp,
        "colour_aware_false_negatives": n - colour_tp,
        "colour_aware_precision": colour_tp / m if m else (1.0 if n == 0 else 0.0),
        "colour_aware_recall": colour_tp / n if n else (1.0 if m == 0 else 0.0),
        "colour_aware_f1": 2 * colour_tp / (n + m) if n + m else 1.0,
        "matches": [
            {
                "reference_id": references[i]["id"],
                "prediction_id": predictions[j]["id"],
                "colour_match": references[i]["colour"] == predictions[j]["colour"] if evaluate_colour else None,
            }
            for i, j in pairs
        ],
        "missed_reference_ids": [r["id"] for i, r in enumerate(references) if i not in used_ref],
        "extra_prediction_ids": [p["id"] for j, p in enumerate(predictions) if j not in used_pred],
        "scoring_tolerance_s": tolerance_s,
        "prediction_time_mode": prediction_time_mode,
        "max_prediction_interval_s": max_prediction_interval_s,
        "timing_interpretation": "Passage detection within a reference interval; no release-time error inferred.",
    }

    result["colour_evaluated"] = evaluate_colour
    if not evaluate_colour:
        for key in result:
            if key.startswith("colour_aware_"):
                result[key] = None
    return result
