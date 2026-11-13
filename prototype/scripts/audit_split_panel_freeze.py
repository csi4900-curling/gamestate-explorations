"""Find long static-left intervals in a 2024 split-screen broadcast.

The detector is an image-motion diagnostic, not a throw detector. It compares
five-second source samples without using any event predictions.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np


def digest(path):
    value = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def motion_mae(previous, current, box):
    x0, y0, x1, y1 = box
    a = previous[y0:y1, x0:x1].astype(np.int16)
    b = current[y0:y1, x0:x1].astype(np.int16)
    return float(np.mean(np.abs(a - b)))


def normalized_split_frame(frame):
    """Measure the same 640×360 panel regions across 16:9 source sizes."""
    height, width = frame.shape[:2]
    if abs(width / height - 16 / 9) > 0.015:
        raise ValueError("Split-panel activity audit expects a 16:9 source")
    if (height, width) == (360, 640):
        return frame
    return cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)


def static_runs(samples, *, max_left_mae, min_duration_s):
    runs = []
    start = None
    edges = []
    for row in samples:
        if row["left_mae"] < max_left_mae:
            if start is None:
                start = row["previous_time_s"]
            edges.append(row)
        else:
            if edges and edges[-1]["time_s"] - start >= min_duration_s:
                runs.append(
                    {
                        "start_s": start,
                        "stop_s": edges[-1]["time_s"],
                        "duration_s": edges[-1]["time_s"] - start,
                        "sample_edge_count": len(edges),
                        "median_left_mae": float(np.median([edge["left_mae"] for edge in edges])),
                        "median_right_mae": float(np.median([edge["right_mae"] for edge in edges])),
                    }
                )
            start, edges = None, []
    if edges and edges[-1]["time_s"] - start >= min_duration_s:
        runs.append(
            {
                "start_s": start,
                "stop_s": edges[-1]["time_s"],
                "duration_s": edges[-1]["time_s"] - start,
                "sample_edge_count": len(edges),
                "median_left_mae": float(np.median([edge["left_mae"] for edge in edges])),
                "median_right_mae": float(np.median([edge["right_mae"] for edge in edges])),
            }
        )
    return runs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--step-s", type=int, default=5)
    parser.add_argument("--max-left-mae", type=float, default=3)
    parser.add_argument("--min-duration-s", type=int, default=60)
    parser.add_argument("--start", type=float, default=0)
    parser.add_argument(
        "--end", type=float, help="End of sampled source interval; defaults to video duration"
    )
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    if args.step_s <= 0 or args.min_duration_s < args.step_s:
        parser.error("Invalid sampling interval")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Could not open source")
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
    end = min(duration, args.end) if args.end is not None else duration
    if not 0 <= args.start < end <= duration:
        parser.error("Invalid sampled source interval")
    previous, previous_t = None, None
    edges = []
    left_box = [0, 15, 310, 350]
    right_box = [325, 15, 635, 350]
    for t in np.arange(args.start, end, args.step_s):
        cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"Could not decode source time {t}")
        frame = normalized_split_frame(frame)
        if previous is not None:
            edges.append(
                {
                    "previous_time_s": previous_t,
                    "time_s": t,
                    "left_mae": round(motion_mae(previous, frame, left_box), 4),
                    "right_mae": round(motion_mae(previous, frame, right_box), 4),
                }
            )
        previous, previous_t = frame, t
    cap.release()
    runs = static_runs(edges, max_left_mae=args.max_left_mae, min_duration_s=args.min_duration_s)
    output = {
        "status": "source_image_panel_freeze_diagnostic_not_throw_truth",
        "source_sha256": digest(args.video),
        "runner_sha256": digest(Path(__file__)),
        "source_duration_s": duration,
        "source_interval_s": [args.start, end],
        "sample_step_s": args.step_s,
        "left_roi_xyxy": left_box,
        "right_roi_xyxy": right_box,
        "static_left_mae_below": args.max_left_mae,
        "minimum_reported_duration_s": args.min_duration_s,
        "static_left_runs": runs,
        "sample_edges": edges,
        "limitations": [
            "Motion is measured between sparse frames, not all source frames.",
            "The threshold was selected after visually noticing this Latvia failure.",
            "A static left panel does not label individual throws or prove right-panel stone identity.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"static_left_runs": runs}))


if __name__ == "__main__":
    main()
