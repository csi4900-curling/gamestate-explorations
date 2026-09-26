"""Run the frozen detector; measure uncensored errors only after image-space association."""

import sys, json, hashlib, csv, shutil
from pathlib import Path
import numpy as np, cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
BASE = ROOT.parent / "feasibility"
OUT = ROOT / "stone-accuracy"
from vision_core import detect_caps
from stone_accuracy import match_observations, position_statistics

protocol = json.loads((OUT / "protocol.json").read_text())
for file, sha in protocol["sha256"].items():
    if hashlib.sha256((ROOT.parent / file).read_bytes()).hexdigest() != sha:
        raise RuntimeError(f"Frozen input changed: {file}")
frames = []
for f in protocol["frames"]:
    image = cv2.imread(str(BASE / f["image"]))
    H = np.array(f["H"])
    h, w = image.shape[:2]
    predictions, diag = detect_caps(
        image, H, {"region": [0, 0, w, h], "world_bounds": [-2.375, -6.401, 2.375, 6.401]}
    )
    for p in predictions:
        p["diagram_metric_m"] = (np.array(p["ice_plane_projection_m"]) * f["diagram_sign"]).tolist()
    pairs, unmatchedp, unmatchedr = match_observations(predictions, f["labels"])
    labels = []
    prediction_status = {}
    for pi, ri in pairs:
        ref = f["labels"][ri]
        pred = predictions[pi]
        prediction_status[pi] = (
            "matched_house" if ref["in_house_scope"] else "matched_outside_house"
        )
        if not ref["in_house_scope"]:
            continue
        row = dict(
            ref,
            prediction_index=pi,
            predicted_metric_m=pred["diagram_metric_m"],
            status="detected",
            pixel_discrepancy=float(np.linalg.norm(np.array(pred["pixel_center"]) - ref["pixel"])),
        )
        if ref["reference_m"] is not None:
            error = np.array(pred["diagram_metric_m"]) - ref["reference_m"]
            row.update(
                error_cm=float(np.linalg.norm(error) * 100),
                error_xy_cm=(error * 100).tolist(),
                manual_error_cm=float(
                    np.linalg.norm(np.array(ref["manual_metric_m"]) - ref["reference_m"]) * 100
                ),
            )
        else:
            row.update(error_cm=None, manual_error_cm=None)
        labels.append(row)
    for ri in unmatchedr:
        ref = f["labels"][ri]
        if ref["in_house_scope"]:
            labels.append(
                dict(
                    ref,
                    status="missed",
                    error_cm=None,
                    manual_error_cm=float(
                        np.linalg.norm(np.array(ref["manual_metric_m"]) - ref["reference_m"]) * 100
                    )
                    if ref["reference_m"] is not None
                    else None,
                )
            )
    false = []
    ignored = []
    for pi in unmatchedp:
        pred = predictions[pi]
        ignore = next(
            (
                r
                for r in f["ignored_moving_stones"]
                if pred["colour"] == r["colour"]
                and np.linalg.norm(np.array(pred["pixel_center"]) - r["pixel"])
                <= r["matching_radius_px"]
            ),
            None,
        )
        if ignore is not None or pred["colour"] not in f["evaluation_colours"]:
            prediction_status[pi] = "ignored_moving_or_unlabelled_colour"
            ignored.append(pi)
        elif np.linalg.norm(pred["diagram_metric_m"]) <= 2:
            prediction_status[pi] = "false_proposal"
            false.append(pi)
        else:
            prediction_status[pi] = "outside_evaluation_domain"
    for pi, p in enumerate(predictions):
        p["evaluation_status"] = prediction_status.get(pi, "outside_evaluation_domain")
    labels = [r for r in labels if r["colour"] in f["evaluation_colours"]]
    result = {k: v for k, v in f.items() if k not in ["H", "labels"]}
    result.update(
        labels=labels,
        predictions=predictions,
        false_proposal_indices=false,
        ignored_prediction_indices=ignored,
        rejected_components=diag["rejected"],
        H=f["H"],
    )
    errors = [r["error_cm"] for r in labels if r["error_cm"] is not None]
    result["summary"] = {
        "visible_targets": len(labels),
        "detected": sum(r["status"] == "detected" for r in labels),
        "missed": sum(r["status"] == "missed" for r in labels),
        "false_proposals": len(false),
        "position": position_statistics(errors),
    }
    frames.append(result)
    shutil.copy2(BASE / f["image"], OUT / "frames" / f"{f['id']}.png")
    diagram = BASE / "sources/official_shot_diagrams" / f"end{f['end']}_shot{f['shot']}.png"
    if diagram.exists():
        shutil.copy2(diagram, OUT / "frames" / diagram.name)
    print(f["id"], result["summary"], flush=True)


def aggregate(subset):
    labels = [r for f in subset for r in f["labels"]]
    tp = sum(r["status"] == "detected" for r in labels)
    fn = len(labels) - tp
    fp = sum(len(f["false_proposal_indices"]) for f in subset)
    eligible = [r for r in labels if r["reference_m"] is not None]
    errors = [r["error_cm"] for r in eligible if r["error_cm"] is not None]
    same = [r["manual_error_cm"] for r in eligible if r["error_cm"] is not None]
    return {
        "frames": len(subset),
        "distinct_end_shot_keys": len({(f["end"], f["shot"]) for f in subset}),
        "visible_targets": len(labels),
        "detected": tp,
        "missed": fn,
        "false_proposals": fp,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / len(labels) if labels else None,
        "reference_linked_targets": len(eligible),
        "automatic_position": position_statistics(errors),
        "manual_position_on_same_detected_subset": position_statistics(same),
        "manual_position_on_all_reference_targets": position_statistics(
            [r["manual_error_cm"] for r in eligible]
        ),
        "within_threshold": {
            str(cm): {
                "detected_within": sum(e <= cm for e in errors),
                "reference_targets": len(eligible),
                "fraction_of_reference_targets": sum(e <= cm for e in errors) / len(eligible)
                if eligible
                else None,
            }
            for cm in protocol["thresholds_cm"]
        },
    }


primary = [f for f in frames if f["primary"]]
result = {
    "protocol_sha256": hashlib.sha256((OUT / "protocol.json").read_bytes()).hexdigest(),
    "summaries": {
        "primary_all": aggregate(primary),
        "primary_overhead": aggregate([f for f in primary if f["tier"] == "overhead"]),
        "primary_oblique": aggregate([f for f in primary if f["tier"] == "oblique"]),
    },
    "frames": frames,
    "claim": "Reference discrepancy for the frozen automatic detector conditional on supplied manual calibration. Not surveyed accuracy, not accuracy of the Canada–Korea clip, and not whole-video reconstruction.",
}
(OUT / "results.json").write_text(
    json.dumps(
        result,
        indent=2,
        allow_nan=False,
        default=lambda v: v.item() if isinstance(v, np.generic) else str(v),
    )
)
rows = []
for f in frames:
    for r in f["labels"]:
        rows.append(
            {
                "frame": f["id"],
                "primary": f["primary"],
                "tier": f["tier"],
                "label": r["id"],
                "colour": r["colour"],
                "status": r["status"],
                "reference_id": r["reference_id"],
                "error_cm": r["error_cm"],
                "manual_error_cm": r["manual_error_cm"],
                "prediction_index": r.get("prediction_index"),
            }
        )
with (OUT / "stone-errors.csv").open("w") as file:
    writer = csv.DictWriter(file, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
print(
    json.dumps(
        result["summaries"],
        indent=2,
        default=lambda v: v.item() if isinstance(v, np.generic) else str(v),
    )
)
