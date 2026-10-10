"""Measure non-ice visual support below a right-view coloured proposal.

The band starts below the small stone body at 360p scale. It may contain a
person's torso/wheelchair under a tracked head, but is only a review cue.
"""

from statistics import median

import cv2


def underpoint_nonice_fraction(
    frame, pixel, *, half_width=20, top_offset=22, bottom_offset=60, min_sample_pixels=300
):
    if frame.shape[:2] != (360, 640):
        raise ValueError("Expected 640x360 source frame")
    cx, cy = map(round, pixel)
    x0, x1 = max(0, cx - half_width), min(640, cx + half_width)
    y0, y1 = max(0, cy + top_offset), min(360, cy + bottom_offset)
    if (x1 - x0) * (y1 - y0) < min_sample_pixels:
        return None
    hsv = cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
    ice = (hsv[:, :, 1] < 90) & (hsv[:, :, 2] > 150)
    return float((~ice).mean())


def three_sample_underpoint(frames, points):
    if len(frames) != len(points) or len(frames) != 3:
        raise ValueError("Expected three matched source frames and track points")
    values = [
        underpoint_nonice_fraction(frame, point["pixel"]) for frame, point in zip(frames, points)
    ]
    available = [value for value in values if value is not None]
    return {
        "sample_underpoint_nonice_fractions": [
            None if value is None else round(value, 4) for value in values
        ],
        "median_underpoint_nonice_fraction": (
            None if not available else round(median(available), 4)
        ),
        "available_sample_count": len(available),
        "coordinate_frame": "640x360_source_right_panel_pixels",
        "physical_stone_identity_verified": False,
    }
