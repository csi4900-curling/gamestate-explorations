"""Scan 2024 broadcast chevrons using two-dimensional panel registration.

This is a development transfer. It preserves the original frozen scan and
does not interpret graphic changes as physical end or throw times.
"""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import statistics
import sys

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from scoreboard_end_marker import read_active_end_marker


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rectangle_fraction(integral, x, y, width, height):
    return (
        integral[y + height, x + width]
        - integral[y, x + width]
        - integral[y + height, x]
        + integral[y, x]
    ) / (width * height)


def panel_shift_2d(frame):
    if frame is None or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("Expected BGR frame")
    hsv = cv2.cvtColor(
        cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2HSV
    )
    red = (
        ((hsv[:, :, 0] < 12) | (hsv[:, :, 0] > 170)) & (hsv[:, :, 1] > 75) & (hsv[:, :, 2] > 60)
    ).astype(np.uint8)
    yellow = (
        (hsv[:, :, 0] > 15) & (hsv[:, :, 0] < 45) & (hsv[:, :, 1] > 75) & (hsv[:, :, 2] > 70)
    ).astype(np.uint8)
    red_integral, yellow_integral = cv2.integral(red), cv2.integral(yellow)
    best = (0.0, None, None)
    for x_shift in range(-5, 46):
        x = 364 + x_shift
        for y_shift in range(-5, 31):
            red_fraction = rectangle_fraction(red_integral, x, 53 + y_shift, 30, 12)
            yellow_fraction = rectangle_fraction(yellow_integral, x, 66 + y_shift, 30, 13)
            score = min(red_fraction, yellow_fraction)
            if score > best[0]:
                best = (score, x_shift, y_shift)
    score, x_shift, y_shift = best
    if score <= 0.35:
        return None
    return {
        "x_shift_px": x_shift,
        "y_shift_px": y_shift,
        "panel_colour_score": round(float(score), 3),
    }


def scan(video, step_s):
    capture = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not capture.isOpened() or fps <= 0:
        raise ValueError(f"Could not open {video}")
    duration = capture.get(cv2.CAP_PROP_FRAME_COUNT) / fps
    calibration = []
    for time_s in range(120, int(duration), 60):
        capture.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
        ok, frame = capture.read()
        if ok:
            location = panel_shift_2d(frame)
            if location is not None:
                calibration.append({"time_s": time_s, **location})
    geometry = None
    if len(calibration) >= 5:
        geometry = {
            "x_shift_px": round(statistics.median(row["x_shift_px"] for row in calibration)),
            "y_shift_px": round(statistics.median(row["y_shift_px"] for row in calibration)),
            "slot_pitch_px": 10.3,
            "calibration_count": len(calibration),
        }
    samples = []
    for time_s in range(0, int(duration), step_s):
        capture.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
        ok, frame = capture.read()
        if not ok:
            samples.append({"time_s": time_s, "marker": None, "frame_read_failed": True})
            continue
        marker = None
        local = None
        if geometry is not None:
            local = panel_shift_2d(frame)
            if (
                local is not None
                and abs(local["x_shift_px"] - geometry["x_shift_px"]) <= 4
                and abs(local["y_shift_px"] - geometry["y_shift_px"]) <= 4
            ):
                # The frozen template expects fixed vertical row coordinates.
                aligned = np.roll(frame, -local["y_shift_px"], axis=0)
                marker = read_active_end_marker(
                    aligned, x_shift_px=local["x_shift_px"], slot_pitch_px=geometry["slot_pitch_px"]
                )
        samples.append({"time_s": time_s, "marker": marker, "local_panel_geometry": local})
    capture.release()
    hits = [row for row in samples if row["marker"] is not None]
    return {
        "status": "development_2d_registered_broadcast_marker_not_physical_end",
        "video_path": str(video),
        "video_sha256": digest(video),
        "frozen_reader_sha256": digest(ROOT / "prototype/scoreboard_end_marker.py"),
        "runner_sha256": digest(Path(__file__)),
        "duration_s": duration,
        "sample_step_s": step_s,
        "sample_count": len(samples),
        "recognized_count": len(hits),
        "calibration": calibration,
        "geometry": geometry,
        "recognized_end_counts": dict(
            sorted(Counter(row["marker"]["end"] for row in hits).items())
        ),
        "samples": samples,
        "limitations": [
            "Panel geometry is fitted from the source but the chevron template and threshold remain from the earlier 2024 reader.",
            "A marker needs source review against the printed column number; image similarity alone is insufficient.",
            "A displayed end can lag physical play and cannot timestamp a throw or physical end transition.",
            "This recording has been exposed during development and is not an independent validation set.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--step-s", type=int, default=10)
    args = parser.parse_args()
    if args.step_s <= 0 or args.output.exists():
        parser.error("Positive step and new output path required")
    result = scan(args.video, args.step_s)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "geometry": result["geometry"],
                "recognized": result["recognized_count"],
                "samples": result["sample_count"],
                "ends": result["recognized_end_counts"],
            }
        )
    )


if __name__ == "__main__":
    main()
