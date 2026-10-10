"""Image-local ice context around a coloured right-view track point."""

from statistics import median

import cv2
import numpy as np


def nonice_ring_fraction(frame, pixel, *, outer_x=28, outer_y=40,
                         inner_half_extent=12):
    if frame.shape[:2] != (360, 640):
        raise ValueError("Expected 640x360 source frame")
    cx, cy = map(round, pixel)
    x0, x1 = max(0, cx - outer_x), min(640, cx + outer_x)
    y0, y1 = max(0, cy - outer_y), min(360, cy + outer_y)
    if x1 <= x0 or y1 <= y0:
        raise ValueError("Track point outside source frame")
    hsv = cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
    yy, xx = np.ogrid[y0:y1, x0:x1]
    ring = ((np.abs(xx - cx) > inner_half_extent) |
            (np.abs(yy - cy) > inner_half_extent))
    ice = (hsv[:, :, 1] < 90) & (hsv[:, :, 2] > 150)
    if ring.sum() < 500:
        raise ValueError("Insufficient surrounding source pixels")
    return float((~ice)[ring].mean())


def three_sample_context(frames, points):
    if len(frames) != len(points) or len(frames) != 3:
        raise ValueError("Expected three matched source frames and track points")
    fractions = [nonice_ring_fraction(frame, point["pixel"])
                 for frame, point in zip(frames, points)]
    return {"sample_nonice_ring_fractions": [round(value, 4) for value in fractions],
            "median_nonice_ring_fraction": round(median(fractions), 4),
            "coordinate_frame": "640x360_source_right_panel_pixels",
            "physical_stone_identity_verified": False}
