"""Verify source-time alignment of a high-resolution interval against a full match."""

import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402


def frame_at(capture, time_s):
    fps = capture.get(cv2.CAP_PROP_FPS)
    capture.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
    ok, frame = capture.read()
    if not ok:
        raise RuntimeError(f"Cannot decode frame at {time_s} s")
    return frame


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-video", type=Path, required=True)
    parser.add_argument("--interval-video", type=Path, required=True)
    parser.add_argument("--source-offset", type=float, required=True)
    parser.add_argument("--times", type=float, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Alignment audit already exists")
    full = cv2.VideoCapture(str(args.full_video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    interval = cv2.VideoCapture(
        str(args.interval_video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1]
    )
    if not full.isOpened() or not interval.isOpened():
        parser.error("Cannot open source videos")
    rows = []
    offsets = [-3.0, -2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 3.0]
    try:
        for source_time in args.times:
            target = cv2.cvtColor(frame_at(full, source_time), cv2.COLOR_BGR2GRAY)
            differences = []
            for delta in offsets:
                comparison = frame_at(interval, source_time - args.source_offset + delta)
                comparison = cv2.resize(
                    comparison, (target.shape[1], target.shape[0]), interpolation=cv2.INTER_AREA
                )
                comparison = cv2.cvtColor(comparison, cv2.COLOR_BGR2GRAY)
                differences.append(float(np.mean(cv2.absdiff(target, comparison))))
            best = offsets[int(np.argmin(differences))]
            rows.append(
                {
                    "source_time_s": source_time,
                    "best_interval_time_adjustment_s": best,
                    "mean_absolute_grayscale_difference_by_adjustment": dict(
                        zip(map(str, offsets), differences)
                    ),
                }
            )
    finally:
        full.release()
        interval.release()
    result = {
        "status": "source_time_alignment_diagnostic",
        "full_video_sha256": file_sha256(args.full_video),
        "interval_video_sha256": file_sha256(args.interval_video),
        "source_offset_s": args.source_offset,
        "rows": rows,
        "all_best_at_zero_adjustment": all(
            row["best_interval_time_adjustment_s"] == 0 for row in rows
        ),
        "runner_sha256": file_sha256(__file__),
        "limitations": [
            "This compares only sampled frames, not every frame or all time-code metadata.",
            "Compression and resizing differences remain in the mean absolute image error.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print([(row["source_time_s"], row["best_interval_time_adjustment_s"]) for row in rows])
    if not result["all_best_at_zero_adjustment"]:
        raise SystemExit("Proposed source offset did not align at all samples")


if __name__ == "__main__":
    main()
