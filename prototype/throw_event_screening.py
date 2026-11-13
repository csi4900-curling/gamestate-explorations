"""Conservative appearance check on recorded passage tracks.

This screen was developed using the archived Canada–Korea passages and two
retrospectively identified player-head tracks in Canada–Slovakia. It is not a
trained or independently validated stone/person classifier.
"""

from __future__ import annotations
import math
import cv2
import numpy as np


SCREEN_VERSION = "passage-appearance-development-v1"
MIN_CAP_VALUE = 80.0
WINDOW_S = 0.30


def appearance_at_crossing(event, capture, fps):
    """Return candidate evidence without discarding the original event."""
    if not capture.isOpened() or not math.isfinite(fps) or fps <= 0:
        raise ValueError("Unreadable video")
    crossing = event["crossing_time_s"]
    nearby = [p for p in event["trajectory"] if abs(p["time_s"] - crossing) <= WINDOW_S]
    levels = []
    for point in nearby:
        capture.set(cv2.CAP_PROP_POS_FRAMES, round(point["time_s"] * fps))
        ok, frame = capture.read()
        if not ok:
            continue
        frame = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
        x, y, w, h = point["bbox"]
        if not all(isinstance(q, (int, float)) and math.isfinite(q) for q in (x, y, w, h)):
            continue
        x, y, w, h = (round(q) for q in (x, y, w, h))
        if w <= 0 or h <= 0 or x < 0 or y < 0 or x + w > 640 or y + h > 360:
            continue
        patch = frame[y : y + max(2, h // 2), x : x + w]
        if not patch.size:
            continue
        value = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)[:, :, 2]
        levels.append({"time_s": point["time_s"], "median_cap_value": float(np.median(value))})
    if not levels:
        return {
            "status": "appearance_unavailable",
            "reason": "No readable source patches around crossing; retain candidate for review.",
            "samples": [],
            "median_cap_value": None,
        }
    median = float(np.median([p["median_cap_value"] for p in levels]))
    return {
        "status": "stone_appearance_candidate"
        if median >= MIN_CAP_VALUE
        else "person_or_other_object_suspected",
        "reason": "Cap-region brightness is a development heuristic, not independent stone identity.",
        "samples": levels,
        "median_cap_value": median,
        "threshold": MIN_CAP_VALUE,
    }
