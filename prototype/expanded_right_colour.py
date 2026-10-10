"""Exposed-match right-colour diagnostic below the frozen 2024 proposal ROI.

This lives separately from the frozen detector so old source/code-hashed
proposal artifacts remain reproducible. It is not a production threshold.
"""

import cv2
import numpy as np


def expanded_right_colour_proposals(frame):
    if frame.shape != (360, 640, 3):
        raise ValueError("Expected 640x360 split source frame")
    hue, saturation, value = cv2.split(cv2.cvtColor(frame, cv2.COLOR_BGR2HSV))
    masks = (
        ("red", ((hue < 12) | (hue > 170)) & (saturation > 70) & (value > 45)),
        ("yellow", (hue > 16) & (hue < 43) & (saturation > 70) & (value > 65)),
    )
    result = {"red": [], "yellow": []}
    for colour, source_mask in masks:
        mask = np.zeros_like(source_mask, dtype=np.uint8)
        mask[145:360, 330:630] = source_mask[145:360, 330:630].astype(np.uint8) * 255
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            x, y, width, height = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            if not (4 <= area <= 220 and 4 <= width <= 24 and 3 <= height <= 16):
                continue
            result[colour].append(
                {
                    "pixel": [x + width / 2, y + height / 2],
                    "bbox": [x, y, width, height],
                    "cap_area_px2": round(float(area), 2),
                }
            )
    return result
