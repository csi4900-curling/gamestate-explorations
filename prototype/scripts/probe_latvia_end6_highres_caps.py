"""Compare native-1080p and 360p right-cap proposals in Latvia's blind interval.

This is a source diagnostic, not stone identity or event validation. All
reported coordinates are normalized to the 640x360 broadcast frame.
"""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from probe_static_left_right_cap_motion import right_colour_proposals
from probe_latvia_end6_lower_cap_direction import link_lower_detections

BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
LOW = BASE / "source-360p.mp4"
HIGH = BASE / "source-1080p-5670-6670.mp4"
OUT = (
    ROOT
    / "validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1/end6-highres-cap-transfer-development.json"
)
START_S, STOP_S = 5670, 6670
ROI = (990, 435, 1890, 975)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def frame_at(capture, seconds):
    capture.set(cv2.CAP_PROP_POS_MSEC, seconds * 1000)
    ok, frame = capture.read()
    if not ok:
        raise RuntimeError(f"Unable to decode {seconds} s")
    return frame


def highres_proposals(frame):
    if frame.shape[:2] != (1080, 1920):
        raise ValueError("Expected native 1080p video")
    x1, y1, x2, y2 = ROI
    hsv = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2HSV)
    hue, saturation, value = cv2.split(hsv)
    masks = {
        "red": ((hue < 12) | (hue > 170)) & (saturation > 70) & (value > 45),
        "yellow": (hue > 16) & (hue < 43) & (saturation > 70) & (value > 65),
    }
    result = {"red": [], "yellow": []}
    for colour, mask in masks.items():
        contours, _ = cv2.findContours(
            mask.astype(np.uint8) * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        for contour in contours:
            x, y, width, height = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            # Same physical proposal box as the 360p lane, with a lower
            # high-resolution area floor to test visibility gained at 1080p.
            if not (12 <= area <= 1080 and 6 <= width <= 72 and 5 <= height <= 48):
                continue
            point = [(x1 + x + width / 2) / 3, (y1 + y + height / 2) / 3]
            result[colour].append(
                {
                    "pixel": [round(v, 2) for v in point],
                    "bbox_1080p": [x1 + x, y1 + y, width, height],
                    "cap_area_1080p_px2": round(float(area), 2),
                }
            )
    return result


def main():
    if OUT.exists():
        raise SystemExit("Output exists; preserve previous diagnostic")
    low = cv2.VideoCapture(str(LOW), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    high = cv2.VideoCapture(str(HIGH), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not low.isOpened() or not high.isOpened():
        raise RuntimeError("Could not open both source videos")
    rows = []
    try:
        for t in range(START_S, STOP_S):
            low_frame = frame_at(low, t)
            high_frame = frame_at(high, t - START_S)
            if low_frame.shape[:2] != (360, 640):
                raise ValueError("Unexpected 360p source dimensions")
            low_points = right_colour_proposals(low_frame)
            high_points = highres_proposals(high_frame)
            lower = {}
            for colour in ("red", "yellow"):
                lower[colour] = []
                for point in high_points[colour]:
                    if point["pixel"][1] < 235:
                        continue
                    nearest = min(
                        (
                            np.hypot(
                                point["pixel"][0] - p["pixel"][0], point["pixel"][1] - p["pixel"][1]
                            )
                            for p in low_points[colour]
                        ),
                        default=float("inf"),
                    )
                    lower[colour].append({**point, "matched_360p_within_5px": bool(nearest <= 5)})
            rows.append({"time_s": t, "lower_colour_proposals": lower})
    finally:
        low.release()
        high.release()
    tracks = link_lower_detections(rows)
    summary = {
        "status": "highres_colour_visibility_diagnostic_not_stone_or_throw_truth",
        "low_video_sha256": digest(LOW),
        "high_video_sha256": digest(HIGH),
        "runner_sha256": digest(Path(__file__)),
        "reference_low_proposal_code_sha256": digest(
            ROOT / "prototype/scripts/probe_static_left_right_cap_motion.py"
        ),
        "linker_code_sha256": digest(
            ROOT / "prototype/scripts/probe_latvia_end6_lower_cap_direction.py"
        ),
        "interval_s": [START_S, STOP_S],
        "sample_period_s": 1,
        "right_roi_1080p_xyxy": ROI,
        "normalization_scale": 3,
        "matched_low_radius_px": 5,
        "lower_y_min_360p": 235,
        "high_contour_area_px2": [12, 1080],
        "lower_proposal_counts": {
            colour: {
                "total": sum(len(r["lower_colour_proposals"][colour]) for r in rows),
                "high_only": sum(
                    not p["matched_360p_within_5px"]
                    for r in rows
                    for p in r["lower_colour_proposals"][colour]
                ),
            }
            for colour in ("red", "yellow")
        },
        "supported_track_direction_counts": dict(
            Counter(f"{r['colour']}_{r['direction']}" for r in tracks)
        ),
        "samples": rows,
        "image_motion_tracks": tracks,
        "limitations": [
            "Lower contour floor at 1080p was chosen for a development visibility probe.",
            "Colour blobs include apparel, equipment, handled and parked stones.",
            "One-second samples and greedy normalized-coordinate links can miss or switch moving stones.",
            "No source review or independent event labels are inferred from proposal counts.",
        ],
    }
    OUT.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "counts": summary["lower_proposal_counts"],
                "tracks": summary["supported_track_direction_counts"],
            }
        )
    )


if __name__ == "__main__":
    main()
