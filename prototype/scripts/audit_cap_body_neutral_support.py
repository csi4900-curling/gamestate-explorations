"""Measure neutral-gray body support below existing cap boxes; no event decision."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402


def body_band(frame, bbox):
    x, y, width, height = bbox
    left = max(0, round(x - width * 0.25))
    right = min(frame.shape[1], round(x + width * 1.25))
    top = min(frame.shape[0], y + height)
    bottom = min(frame.shape[0], round(y + height + width * 0.85))
    if left >= right or top >= bottom:
        return None
    hsv = cv2.cvtColor(frame[top:bottom, left:right], cv2.COLOR_BGR2HSV)
    _, saturation, value = cv2.split(hsv)
    return {
        "bbox_px": [left, top, right - left, bottom - top],
        "neutral_gray_fraction": float(np.mean((saturation < 65) &
                                               (value >= 55) & (value <= 195))),
        "dark_fraction": float(np.mean(value < 75)),
        "white_fraction": float(np.mean((saturation < 45) & (value > 195))),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "patch", "screen", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--source-offset", type=float, default=0.0)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Audit already exists")
    patch = json.loads(args.patch.read_text())
    screen = json.loads(args.screen.read_text())
    if (file_sha256(args.video) != patch["video_sha256"] or
            file_sha256(args.patch) != screen["patch_sha256"]):
        parser.error("Video, patch and screen hashes do not chain")
    decisions = {row["candidate_id"]: row for row in screen["decisions"]}
    rows = {row["candidate_id"]: row for row in patch["rows"]}
    if (len(decisions) != len(screen["decisions"]) or
            len(rows) != len(patch["rows"]) or set(decisions) != set(rows)):
        parser.error("Patch and screen candidate coverage differs")
    video = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                             [cv2.CAP_PROP_N_THREADS, 1])
    if not video.isOpened():
        parser.error("Cannot open video")
    fps = video.get(cv2.CAP_PROP_FPS)
    output_rows = []
    try:
        for pid, decision in decisions.items():
            if not decision["accepted"]:
                continue
            samples = []
            for sample in rows[pid]["samples"]:
                if sample["status"] != "scored":
                    continue
                t = sample["source_time_s"]
                video.set(cv2.CAP_PROP_POS_FRAMES,
                          round((t - args.source_offset) * fps))
                ok, frame = video.read()
                if not ok:
                    raise RuntimeError(f"Cannot read {pid} at {t}")
                features = body_band(frame, sample["cap_bbox_1080p"])
                samples.append({
                    "source_time_s": t,
                    "patch_score": sample["patch_score"],
                    "patch_accepted": sample["patch_accepted"],
                    "cap_bbox_px": sample["cap_bbox_1080p"],
                    "body_band": features,
                })
            fractions = [s["body_band"]["neutral_gray_fraction"] for s in samples
                         if s["body_band"] is not None]
            output_rows.append({
                "candidate_id": pid,
                "scored_patch_count": len(samples),
                "measurable_body_band_count": len(fractions),
                "max_neutral_gray_fraction": max(fractions) if fractions else None,
                "samples": samples,
            })
    finally:
        video.release()
    result = {
        "status": "postscore_body_band_feature_audit_not_event_validation",
        "source_id": screen["source_id"],
        "source_sha256": screen["source_sha256"],
        "high_resolution_source_sha256": file_sha256(args.video),
        "patch_sha256": file_sha256(args.patch),
        "screen_sha256": file_sha256(args.screen),
        "source_offset_s": args.source_offset,
        "runner_sha256": file_sha256(Path(__file__)),
        "feature_definition": {
            "horizontal_band": "cap bbox x - 0.25w through x + 1.25w, clipped to source",
            "vertical_band": "cap bbox bottom through bottom + 0.85w, clipped to source",
            "neutral_gray_pixel": "HSV saturation < 65 and value in [55, 195]",
            "candidate_summary": "maximum measurable fraction among the existing three patch samples",
        },
        "accepted_candidate_count": len(output_rows),
        "measurable_sample_count": sum(r["measurable_body_band_count"] for r in output_rows),
        "body_band_count_distribution": dict(Counter(r["measurable_body_band_count"]
                                                    for r in output_rows)),
        "rows": output_rows,
        "limitations": [
            "Feature geometry and thresholds were explored after source-reviewing this match's false positives.",
            "Neutral-gray pixels can come from ice, clothing or graphics, and a real stone can be occluded.",
            "This is a feature audit, not an independent throw-event score or calibrated stone-body segmentation.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(len(output_rows), "accepted candidates; measurable samples",
          result["measurable_sample_count"])


if __name__ == "__main__":
    main()
