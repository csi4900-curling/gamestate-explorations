"""Development audit: measure a large dark object above accepted cap patches.

This is an image feature, not a stone/throw classifier. It deliberately uses
only the frozen patch-positive samples and never changes the frozen screen.
"""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np


def digest(path):
    value = sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def overhead_dark_fraction(frame, bbox):
    """Dark fraction in the central column, 15–100 px above a cap box."""
    x, y, width, _ = bbox
    x0 = max(0, x + round(width * 0.15))
    x1 = min(frame.shape[1], x + round(width * 0.85))
    y0 = y - 100
    y1 = y - 15
    if y0 < 0 or y1 > frame.shape[0] or x1 - x0 < 8:
        return None
    patch = frame[y0:y1, x0:x1]
    if patch.shape[:2] != (85, x1 - x0):
        return None
    return float(np.mean(cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)[:, :, 2] < 100))


def audit(features, cap, *, threshold=0.75):
    rows = []
    offset = features["source_offset_s"]
    for item in features["rows"]:
        samples = []
        for sample in item["samples"]:
            if not sample["patch_accepted"]:
                continue
            t = sample["source_time_s"]
            cap.set(cv2.CAP_PROP_POS_MSEC, (t - offset) * 1000)
            ok, frame = cap.read()
            fraction = overhead_dark_fraction(frame, sample["cap_bbox_px"]) if ok else None
            samples.append({"source_time_s": t,
                            "cap_bbox_px": sample["cap_bbox_px"],
                            "dark_fraction": fraction,
                            "decoded_frame_index": int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1 if ok else None})
        if not samples:
            raise ValueError(f"No patch-positive samples for {item['candidate_id']}")
        values = [sample["dark_fraction"] for sample in samples]
        complete = all(value is not None for value in values)
        flagged = complete and min(values) >= threshold
        rows.append({"candidate_id": item["candidate_id"],
                     "positive_patch_count": len(samples),
                     "all_positive_samples_measured": complete,
                     "minimum_overhead_dark_fraction": min(values) if complete else None,
                     "would_abstain": flagged,
                     "samples": samples})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    features = json.loads(args.features.read_text())
    video_hash = digest(args.video)
    if video_hash != features["high_resolution_source_sha256"]:
        parser.error("Video does not match the feature audit")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open video")
    try:
        rows = audit(features, cap)
    finally:
        cap.release()
    if len(rows) != features["accepted_candidate_count"] or len({r["candidate_id"] for r in rows}) != len(rows):
        raise ValueError("Accepted candidate coverage is incomplete")
    output = {
        "status": "postscore_development_overhead_darkness_not_throw_validation",
        "source_id": features["source_id"],
        "source_sha256": features["source_sha256"],
        "high_resolution_source_sha256": video_hash,
        "body_band_feature_sha256": digest(args.features),
        "runner_sha256": digest(Path(__file__)),
        "source_offset_s": features["source_offset_s"],
        "feature_definition": "Fraction with HSV value <100 in central 70% of the cap width, 15–100 pixels above each frozen patch-positive cap box at 1080p.",
        "development_abstention_threshold": 0.75,
        "candidate_count": len(rows),
        "would_abstain_candidate_ids": [r["candidate_id"] for r in rows if r["would_abstain"]],
        "measurement_status_counts": dict(Counter("complete" if r["all_positive_samples_measured"] else "incomplete" for r in rows)),
        "rows": rows,
        "limitations": [
            "The geometry and threshold were selected after inspecting exposed Czechia S96 and S143; this is development, not independent precision or recall.",
            "An isolated true stone can appear below another dark object or rink graphic; a dark-overhead measurement is not object identity.",
            "Only already accepted paths and their patch-positive samples are measured; missed throws are outside this audit.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(len(rows), "accepted candidates; would abstain", output["would_abstain_candidate_ids"])


if __name__ == "__main__":
    main()
