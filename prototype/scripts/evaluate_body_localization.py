"""Compare a new model against the unchanged benchmark, writing a separate run."""

import sys, json, hashlib, csv
from pathlib import Path
import cv2, numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "body-localization"
BASE = ROOT.parent / "feasibility"
from body_localization import detect_and_localize, VERSION
from vision_core import project
from stone_accuracy import match_observations, position_statistics

protocol = json.loads((ROOT / "stone-accuracy/protocol.json").read_text())
for file, sha in protocol["sha256"].items():
    if hashlib.sha256((ROOT.parent / file).read_bytes()).hexdigest() != sha:
        raise RuntimeError(f"Frozen baseline input changed: {file}")
frames = []
for f in protocol["frames"]:
    image = cv2.imread(str(BASE / f["image"]))
    h, w = image.shape[:2]
    predictions, details = detect_and_localize(
        image,
        np.array(f["H"]),
        {"region": [0, 0, w, h], "world_bounds": [-2.375, -6.401, 2.375, 6.401]},
    )
    for p in predictions:
        p["diagram_metric_m"] = (
            (np.array(p["ground_position_m"]) * f["diagram_sign"]).tolist()
            if p["ground_position_m"] is not None
            else None
        )
        p["uncorrected_diagram_m"] = (
            np.array(
                p["localization"].get(
                    "uncorrected_position_m", project(np.array(f["H"]), [p["pixel_center"]])[0]
                )
            )
            * f["diagram_sign"]
        ).tolist()
    pairs, up, ur = match_observations(predictions, f["labels"])
    labels = []
    statuses = {}
    for pi, ri in pairs:
        ref = f["labels"][ri]
        p = predictions[pi]
        statuses[pi] = "matched_house" if ref["in_house_scope"] else "matched_outside_house"
        if not ref["in_house_scope"]:
            continue
        r = dict(
            ref,
            prediction_index=int(pi),
            status="detected",
            predicted_metric_m=p["diagram_metric_m"],
            error_cm=None,
            uncorrected_error_cm=None,
        )
        if ref["reference_m"] is not None and p["diagram_metric_m"] is not None:
            r["error_cm"] = float(
                np.linalg.norm(np.array(p["diagram_metric_m"]) - ref["reference_m"]) * 100
            )
            r["uncorrected_error_cm"] = float(
                np.linalg.norm(np.array(p["uncorrected_diagram_m"]) - ref["reference_m"]) * 100
            )
        labels.append(r)
    for ri in ur:
        ref = f["labels"][ri]
        if ref["in_house_scope"]:
            labels.append(dict(ref, status="missed", error_cm=None, uncorrected_error_cm=None))
    false = []
    ignored = []
    for pi in up:
        p = predictions[pi]
        ignore = next(
            (
                r
                for r in f["ignored_moving_stones"]
                if r["colour"] == p["colour"]
                and np.linalg.norm(np.array(p["pixel_center"]) - r["pixel"])
                <= r["matching_radius_px"]
            ),
            None,
        )
        if ignore is not None or p["colour"] not in f["evaluation_colours"]:
            statuses[pi] = "ignored_moving_or_unlabelled_colour"
            ignored.append(int(pi))
        elif (
            np.linalg.norm(
                p["diagram_metric_m"]
                if p["diagram_metric_m"] is not None
                else p["uncorrected_diagram_m"]
            )
            <= 2
        ):
            statuses[pi] = "false_proposal"
            false.append(int(pi))
        else:
            statuses[pi] = "outside_evaluation_domain"
    for i, p in enumerate(predictions):
        p["evaluation_status"] = statuses.get(i, "outside_evaluation_domain")
    labels = [r for r in labels if r["colour"] in f["evaluation_colours"]]
    row = dict(
        f,
        labels=labels,
        predictions=predictions,
        false_proposal_indices=false,
        ignored_prediction_indices=ignored,
        detector=details,
    )
    row["summary"] = {
        "visible_targets": len(labels),
        "detected": sum(r["status"] == "detected" for r in labels),
        "localized": sum(r.get("predicted_metric_m") is not None for r in labels),
        "missed": sum(r["status"] == "missed" for r in labels),
        "false_proposals": len(false),
        "position": position_statistics(
            [r["error_cm"] for r in labels if r["error_cm"] is not None]
        ),
    }
    frames.append(row)
    print(f["id"], row["summary"], flush=True)


def summary(fs):
    labels = [r for f in fs for r in f["labels"]]
    eligible = [r for r in labels if r["reference_m"] is not None]
    errors = [r["error_cm"] for r in eligible if r["error_cm"] is not None]
    tp = sum(r["status"] == "detected" for r in labels)
    fp = sum(len(f["false_proposal_indices"]) for f in fs)
    return {
        "frames": len(fs),
        "visible_targets": len(labels),
        "detected": tp,
        "localized": sum(r.get("predicted_metric_m") is not None for r in labels),
        "missed": len(labels) - tp,
        "false_proposals": fp,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / len(labels) if labels else None,
        "reference_linked_targets": len(eligible),
        "automatic_position": position_statistics(errors),
        "uncorrected_same_detections": position_statistics(
            [r["uncorrected_error_cm"] for r in eligible if r["uncorrected_error_cm"] is not None]
        ),
        "within_threshold": {
            str(t): {
                "detected_within": sum(e <= t for e in errors),
                "reference_targets": len(eligible),
            }
            for t in protocol["thresholds_cm"]
        },
    }


primary = [f for f in frames if f["primary"]]
result = {
    "version": VERSION,
    "model_sha256": hashlib.sha256((ROOT / "body_localization.py").read_bytes()).hexdigest(),
    "protocol_sha256": hashlib.sha256(
        (ROOT / "stone-accuracy/protocol.json").read_bytes()
    ).hexdigest(),
    "evaluation_scope": "Development comparison on the previously inspected frozen benchmark. Not held-out accuracy. No model inference reads labels or diagram positions.",
    "summaries": {
        "primary_all": summary(primary),
        "primary_overhead": summary([f for f in primary if f["tier"] == "overhead"]),
        "primary_oblique": summary([f for f in primary if f["tier"] == "oblique"]),
    },
    "frames": frames,
}
(OUT / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False))
print(json.dumps(result["summaries"], indent=2))
with (OUT / "stone-errors.csv").open("w") as file:
    rows = [
        {
            "frame": f["id"],
            "primary": f["primary"],
            "tier": f["tier"],
            "stone": r["id"],
            "status": r["status"],
            "error_cm": r["error_cm"],
            "uncorrected_error_cm": r["uncorrected_error_cm"],
        }
        for f in frames
        for r in f["labels"]
    ]
    writer = csv.DictWriter(file, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
