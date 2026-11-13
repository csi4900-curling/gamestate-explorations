"""2024 right-view colour proposals with a development high-recall area cap."""

import cv2
import numpy as np


def right_large_cap_proposals(frame, *, max_contour_area_px2=180):
    if frame.shape[:2] != (360, 640):
        raise ValueError("Expected 640x360 source frame")
    hue, saturation, value = cv2.split(cv2.cvtColor(frame, cv2.COLOR_BGR2HSV))
    masks = (
        ("red", ((hue < 12) | (hue > 170)) & (saturation > 70) & (value > 45)),
        ("yellow", (hue > 16) & (hue < 43) & (saturation > 70) & (value > 65)),
    )
    result = {"red": [], "yellow": []}
    for colour, mask in masks:
        mask[:145] = False
        mask[325:] = False
        mask[:, :330] = False
        mask[:, 630:] = False
        contours, _ = cv2.findContours(
            mask.astype(np.uint8) * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        for contour in contours:
            x, y, width, height = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            if not (4 <= area <= max_contour_area_px2 and 4 <= width <= 24 and 3 <= height <= 16):
                continue
            result[colour].append(
                {
                    "pixel": [x + width / 2, y + height / 2],
                    "bbox": [x, y, width, height],
                    "cap_area_px2": round(float(area), 2),
                }
            )
    return result
