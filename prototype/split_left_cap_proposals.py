"""Raw colour components on the left house of a 640x360 split broadcast."""

import cv2
import numpy as np


LEFT_ROI_XYXY = (0, 120, 320, 335)


def left_colour_cap_proposals(frame, *, roi_xyxy=LEFT_ROI_XYXY):
    if frame.shape != (360, 640, 3):
        raise ValueError("Expected 640x360 split source frame")
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    hue, saturation, value = cv2.split(hsv)
    masks = (
        ("red", ((hue < 12) | (hue > 170)) & (saturation > 70) & (value > 45)),
        ("yellow", (hue > 16) & (hue < 43) & (saturation > 70) & (value > 65)),
    )
    x1, y1, x2, y2 = roi_xyxy
    if not (0 <= x1 < x2 <= 320 and 0 <= y1 < y2 <= 360):
        raise ValueError("Invalid left-panel ROI")
    result = []
    for colour, source_mask in masks:
        mask = np.zeros_like(source_mask, dtype=np.uint8)
        mask[y1:y2, x1:x2] = source_mask[y1:y2, x1:x2].astype(np.uint8) * 255
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            x, y, width, height = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            if not (4 <= area <= 300 and 4 <= width <= 36 and 3 <= height <= 32):
                continue
            result.append({"colour": colour,
                           "pixel": [x + width / 2, y + height / 2],
                           "bbox": [x, y, width, height],
                           "cap_area_px2": round(float(area), 2)})
    return sorted(result, key=lambda item: (item["colour"], item["pixel"][0],
                                             item["pixel"][1]))
