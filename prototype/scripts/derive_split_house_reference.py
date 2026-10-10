"""Derive a temporal-median right-house image reference for each routed run."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from split_house_reference import fit_right_house_paint, right_house_paint_mask

FRAME_COUNT = 65


def digest(path):
    value = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    timeline = json.loads(args.timeline.read_text())
    source_hash = digest(args.video)
    if timeline["source_sha256"] != source_hash:
        parser.error("Source fingerprints differ")
    runs = {row["id"]: row for row in timeline["supported_runs"]
            if row["layout"] == "split_2024"}
    if args.run_id not in runs:
        parser.error("Run is not a supported split view")
    start, end = runs[args.run_id]["interval_s"]
    margin = min(15, (end - start) / 10)
    times = [round(float(value), 3) for value in
             np.linspace(start + margin, end - margin, FRAME_COUNT)]
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Unreadable source video")
    frames = []
    try:
        for t in times:
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ok, frame = cap.read()
            if not ok or frame.shape != (360, 640, 3):
                raise RuntimeError(f"Cannot decode 640x360 source at {t}")
            frames.append(frame)
    finally:
        cap.release()
    reference = np.median(np.stack(frames), axis=0).astype(np.uint8)
    ellipse = fit_right_house_paint(reference)
    selected = [0, 8, 16, 24, 32, 40, 48, 56, 64]
    frame_checks = []
    for index in selected:
        candidate = fit_right_house_paint(frames[index])
        if ellipse and candidate:
            center_shift = round(float(np.linalg.norm(np.asarray(candidate["center_px"])
                                                      - np.asarray(ellipse["center_px"]))), 3)
        else:
            center_shift = None
        frame_checks.append({"source_time_s": times[index],
                             "single_frame_house_ellipse": candidate,
                             "center_shift_from_temporal_median_px": center_shift})
    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    median_path = output.with_name(output.stem + '-median.png')
    mask_path = output.with_name(output.stem + '-paint-mask.png')
    if median_path.exists() or mask_path.exists():
        parser.error("Reference images already exist")
    cv2.imwrite(str(median_path), reference)
    cv2.imwrite(str(mask_path), right_house_paint_mask(reference) * 255)
    result = {
        "status": "source_temporal_median_right_house_image_reference_not_physical_calibration",
        "source_sha256": source_hash,
        "timeline_sha256": digest(args.timeline),
        "run_id": args.run_id,
        "run_interval_s": [start, end],
        "sampled_source_times_s": times,
        "sample_count": len(frames),
        "median_image": median_path.name,
        "median_image_sha256": digest(median_path),
        "paint_mask_image": mask_path.name,
        "paint_mask_sha256": digest(mask_path),
        "temporal_median_house_ellipse": ellipse,
        "single_frame_checks": frame_checks,
        "feature_code_sha256": digest(ROOT / "prototype/split_house_reference.py"),
        "runner_sha256": digest(Path(__file__)),
        "limitations": [
            "A temporal median assumes the split camera and painted house remain aligned during this routed run.",
            "The paint ellipse covers the scoring house only, not guard stones or the complete board.",
            "Single-frame ellipse failures can reflect player occlusion or a camera/layout change.",
            "Image coordinates are not validated metric rink coordinates or simulation-ready geometry.",
        ],
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"run": args.run_id, "ellipse": ellipse,
                      "single_frame_detected": sum(row["single_frame_house_ellipse"] is not None
                                                   for row in frame_checks)}))


if __name__ == "__main__":
    main()
