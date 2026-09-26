"""Visible cap matching, not stone-ground-position or complete-board evaluation."""

from pathlib import Path
import argparse, json, math
import numpy as np

ROOT = Path(__file__).resolve().parents[1] / "vision"
p = argparse.ArgumentParser()
p.add_argument("--include-check", action="store_true")
a = p.parse_args()
references = json.loads((ROOT / "annotations/detection-reference.json").read_text())
results = json.loads((ROOT / "results.json").read_text())
lookup = {(r["timestamp_s"], r["panel"]): r for r in results["observations"]}
frames = []
for ref in references["frames"]:
    if ref["split"] == "check" and not a.include_check:
        continue
    r = lookup[(ref["timestamp_s"], ref["panel"])]
    ignore = ref["ignore_boxes"]
    pred = [
        d
        for d in r["candidates"]
        if not any(
            x0 <= d["pixel_center"][0] <= x1 and y0 <= d["pixel_center"][1] <= y1
            for x0, y0, x1, y1 in ignore
        )
    ]
    pairs = []
    for i, d in enumerate(pred):
        for j, (x, y, colour) in enumerate(ref["caps"]):
            distance = math.dist(d["pixel_center"], [x, y])
            if d["colour"] == colour and distance <= references["matching_threshold_px"]:
                pairs.append((distance, i, j))
    used_pred = set()
    used_ref = set()
    errors = []
    for distance, i, j in sorted(pairs):
        if i not in used_pred and j not in used_ref:
            used_pred.add(i)
            used_ref.add(j)
            errors.append(distance)
    frames.append(
        {
            "timestamp_s": ref["timestamp_s"],
            "panel": ref["panel"],
            "split": ref["split"],
            "registration_status": r["registration"]["status"],
            "reference_caps": len(ref["caps"]),
            "predicted_caps": len(pred),
            "ignored_predictions": len(r["candidates"]) - len(pred),
            "true_positive": len(errors),
            "false_positive": len(pred) - len(errors),
            "false_negative": len(ref["caps"]) - len(errors),
            "matched_errors_px": errors,
            "unmatched_predictions": [d for i, d in enumerate(pred) if i not in used_pred],
            "unmatched_references": [d for i, d in enumerate(ref["caps"]) if i not in used_ref],
        }
    )
summaries = {}
for split in sorted(set(f["split"] for f in frames)):
    fs = [f for f in frames if f["split"] == split]
    tp = sum(f["true_positive"] for f in fs)
    fp = sum(f["false_positive"] for f in fs)
    fn = sum(f["false_negative"] for f in fs)
    errors = [e for f in fs for e in f["matched_errors_px"]]
    summaries[split] = {
        "panel_frames": len(fs),
        "reference_caps": tp + fn,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "matched_median_error_px": float(np.median(errors)) if errors else None,
        "matched_rmse_px": float(np.sqrt(np.mean(np.square(errors)))) if errors else None,
    }
out = {
    "detector_sha256": results["detector_sha256"],
    "matching_threshold_px": references["matching_threshold_px"],
    "method": "Same-colour one-to-one greedy nearest matching within 20 source pixels; fully hidden and explicitly ignored ambiguous caps excluded.",
    "scope": "Same-match AI-annotated exploratory check; not independent human labels, held-out event generalisation, complete-state accuracy or physical-position error.",
    "summaries": summaries,
    "frames": frames,
}
name = "evaluation.json" if a.include_check else "development-evaluation.json"
(ROOT / name).write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(summaries, indent=2))
for f in frames:
    if f["false_positive"] or f["false_negative"]:
        print(
            f["timestamp_s"],
            f["panel"],
            "FP",
            [(d["colour"], d["pixel_center"]) for d in f["unmatched_predictions"]],
            "FN",
            f["unmatched_references"],
        )
