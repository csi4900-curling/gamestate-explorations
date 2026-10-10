#!/usr/bin/env python3
"""Image-mask repeat diagnostic for one visible curling-stone handle.

This estimates a silhouette repeat interval, not a physical revolution count.
"""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "prototype/throw-analysis/end3.mp4"
CROSS_VIEW = ROOT / "prototype/cross-view/results.json"
SOURCE_META = ROOT / "prototype/throw-analysis/source.json"
OUTPUT = ROOT / "validation/spin-observability/T11-handle-periodicity-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def track_pixels(throw, times, *, settled=False):
    points = throw["raw_arrival" if settled else "display_arrival"]
    points = [p for p in points if (2319 <= p["time_s"] <= 2323.5 if settled
                                     else 2307 <= p["time_s"] <= 2312.5)]
    pt = np.array([p["time_s"] for p in points])
    return [(int(round(np.interp(t, pt, [p["pixel"][0] for p in points]))),
             int(round(np.interp(t, pt, [p["pixel"][1] for p in points]))))
            for t in times]


def normalized_yellow_mask(frame, x, y):
    patch = frame[y - 40:y + 8, x - 40:x + 40]
    if patch.shape[:2] != (48, 80):
        return None
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
    mask = (((hsv[:, :, 0] > 16) & (hsv[:, :, 0] < 42) &
             (hsv[:, :, 1] > 65) & (hsv[:, :, 2] > 75))).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    if count < 2:
        return None
    component = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    mask = (labels == component).astype(np.uint8)
    yy, xx = np.where(mask)
    if len(xx) < 100:
        return None
    xmin, xmax = int(xx.min()), int(xx.max())
    bottom = int(yy.max())
    scale = 64 / (xmax - xmin + 1)
    width = round(mask.shape[1] * scale)
    height = round(mask.shape[0] * scale)
    resized = cv2.resize(mask, (width, height), interpolation=cv2.INTER_NEAREST)
    center_x = round((xmin + xmax) / 2 * scale)
    bottom_y = round(bottom * scale)
    canvas = np.zeros((56, 80), np.uint8)
    x0, y0 = 40 - center_x, 48 - bottom_y
    left, top = max(0, x0), max(0, y0)
    right, low = min(80, x0 + width), min(56, y0 + height)
    if right <= left or low <= top:
        return None
    canvas[top:low, left:right] = resized[top - y0:low - y0,
                                       left - x0:right - x0]
    return canvas[:35, :]


def mask_series(cap, throw, times, offset_s, *, settled=False):
    coords = track_pixels(throw, times, settled=settled)
    masks = []
    retained_times = []
    for t, (x, y) in zip(times, coords):
        cap.set(cv2.CAP_PROP_POS_MSEC, (t - offset_s) * 1000)
        ok, frame = cap.read()
        if not ok:
            continue
        mask = normalized_yellow_mask(frame, x, y)
        if mask is not None:
            masks.append(mask)
            retained_times.append(round(float(t), 3))
    return np.array(masks), retained_times


def lag_curve(masks, max_lag_steps):
    rows = []
    for steps in range(1, max_lag_steps + 1):
        a, b = masks[:-steps], masks[steps:]
        if len(a) < 8:
            break
        intersection = (a * b).sum(axis=(1, 2))
        union = ((a + b) > 0).sum(axis=(1, 2))
        similarities = intersection / np.maximum(union, 1)
        rows.append({"lag_s": round(steps / 10, 1),
                     "mean_mask_iou": round(float(similarities.mean()), 4),
                     "frame_pair_count": len(similarities)})
    return rows


def main():
    if OUTPUT.exists():
        raise SystemExit("T11 periodicity artifact already exists")
    meta = json.loads(SOURCE_META.read_text())
    cross_view = json.loads(CROSS_VIEW.read_text())
    throw = next(row for row in cross_view["throws"] if row["id"] == "T11")
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise SystemExit("Cannot open source video")
    try:
        moving_times = np.round(np.arange(2307.0, 2312.51, 0.1), 3)
        settled_times = np.round(np.arange(2319.5, 2323.01, 0.1), 3)
        moving, moving_retained = mask_series(cap, throw, moving_times,
                                              meta["source_interval_s"][0])
        settled, settled_retained = mask_series(cap, throw, settled_times,
                                                meta["source_interval_s"][0], settled=True)
    finally:
        cap.release()
    if len(moving) != len(moving_times) or len(settled) != len(settled_times):
        raise SystemExit("Some sampled frames or yellow masks are missing")
    moving_curve = lag_curve(moving, 35)
    settled_curve = lag_curve(settled, 30)
    repeat_candidates = [row for row in moving_curve if 0.8 <= row["lag_s"] <= 3.0]
    strongest = max(repeat_candidates, key=lambda row: row["mean_mask_iou"])
    result = {
        "status": "exploratory_handle_silhouette_repeat_not_revolution_count",
        "source_video_sha256": digest(VIDEO),
        "source_metadata_sha256": digest(SOURCE_META),
        "cross_view_results_sha256": digest(CROSS_VIEW),
        "runner_sha256": digest(Path(__file__)),
        "moving_source_interval_s": [float(moving_times[0]), float(moving_times[-1])],
        "settled_control_source_interval_s": [float(settled_times[0]), float(settled_times[-1])],
        "sample_rate_hz": 10,
        "moving_sample_count": len(moving_retained),
        "settled_control_sample_count": len(settled_retained),
        "moving_lag_curve": moving_curve,
        "settled_control_lag_curve": settled_curve,
        "strongest_moving_repeat_lag_0_8_to_3_s": strongest,
        "limitations": [
            "The reference positions come from a provisional cross-view stone track.",
            "The descriptor is a side-view yellow silhouette; view geometry and compression can change its shape.",
            "A repeated silhouette may not map one-to-one to a complete physical turn without phase calibration.",
            "No revolution count for the full throw or uncertainty interval is measured.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in
                      ("moving_sample_count", "settled_control_sample_count",
                       "strongest_moving_repeat_lag_0_8_to_3_s")}, indent=2))


if __name__ == "__main__":
    main()
