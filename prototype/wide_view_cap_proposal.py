"""Cap proposals over both white ice and the blue house ring in wide views."""

import cv2
import numpy as np


def wide_view_cap_candidates(frame, colour, ellipse, *, max_ring_distance=2.2):
    """Return source-pixel candidates for later patch and body verification.

    Unlike the delivery-ice proposal, this accepts blue-ring surroundings.
    The wide-house ellipse limits proposals to the observed house region and
    nearby stones; no official board positions are used.
    """
    if colour not in ("red", "yellow"):
        raise ValueError("Unsupported stone colour")
    if frame is None or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("Expected BGR frame")
    if ellipse is None:
        raise ValueError("A source-detected wide house ellipse is required")
    image = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hue, saturation, value = cv2.split(hsv)
    if colour == "red":
        mask = ((hue < 12) | (hue > 170)) & (saturation > 85) & (value > 50)
    else:
        mask = (hue > 16) & (hue < 43) & (saturation > 85) & (value > 70)
    mask[:70] = False
    contours, _ = cv2.findContours(mask.astype("uint8") * 255,
                                   cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cx, cy = ellipse["center_px"]
    rx = max(ellipse["axis_lengths_px"]) / 2
    ry = min(ellipse["axis_lengths_px"]) / 2
    candidates = []
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)
        if not (30 <= area <= 4000 and 8 <= width <= 160
                and 4 <= height <= 80):
            continue
        px, py = x + width / 2, y + height / 2
        ring_distance = np.hypot((px - cx) / rx, (py - cy) / ry)
        if ring_distance > max_ring_distance:
            continue
        x0, x1 = max(0, x - 6), min(640, x + width + 6)
        y0, y1 = max(0, y - 6), min(360, y + height + 6)
        patch = hsv[y0:y1, x0:x1]
        outside = np.ones(patch.shape[:2], dtype=bool)
        outside[y - y0:y + height - y0, x - x0:x + width - x0] = False
        if not outside.any():
            continue
        white = (patch[:, :, 1] < 95) & (patch[:, :, 2] > 150)
        blue = ((patch[:, :, 0] >= 90) & (patch[:, :, 0] <= 130)
                & (patch[:, :, 1] >= 70) & (patch[:, :, 2] >= 50))
        neutral = ((patch[:, :, 1] < 90) & (patch[:, :, 2] > 40)
                   & (patch[:, :, 2] < 190))
        surround_fraction = float((white | blue)[outside].mean())
        neutral_fraction = float(neutral[outside].mean())
        if surround_fraction < 0.45 or (neutral_fraction < 0.30
                                       and surround_fraction < 0.65):
            continue
        candidates.append({
            "pixel": [px, py], "bbox": [x, y, width, height],
            "cap_area_px2": area,
            "neutral_surround_fraction": neutral_fraction,
            "white_or_blue_surround_fraction": surround_fraction,
            "ellipse_ring_distance": round(float(ring_distance), 3),
        })
    return candidates
