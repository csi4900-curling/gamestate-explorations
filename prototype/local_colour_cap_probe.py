"""Return raw local colour components without inventing track identity."""

import cv2
import numpy as np


def local_cap_components(frame, roi_xyxy, colour, *, minimum_area_px2=20):
    if frame is None or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("Expected BGR source frame")
    if colour not in ("red", "yellow"):
        raise ValueError("Unsupported cap colour")
    x0, y0, x1, y1 = roi_xyxy
    if not (
        0 <= x0 < x1 <= frame.shape[1] and 0 <= y0 < y1 <= frame.shape[0] and minimum_area_px2 >= 0
    ):
        raise ValueError("Invalid local ROI or area threshold")
    hsv = cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
    hue, saturation, value = cv2.split(hsv)
    if colour == "red":
        mask = ((hue < 12) | (hue > 170)) & (saturation > 85) & (value > 50)
    else:
        mask = (hue > 16) & (hue < 43) & (saturation > 85) & (value > 70)
    contours, _ = cv2.findContours(
        mask.astype(np.uint8) * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    rows = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < minimum_area_px2:
            continue
        moments = cv2.moments(contour)
        if moments["m00"] <= 0:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        rows.append(
            {
                "area_px2": round(float(area), 3),
                "centroid_px_1080": [
                    round(x0 + moments["m10"] / moments["m00"], 3),
                    round(y0 + moments["m01"] / moments["m00"], 3),
                ],
                "bbox_xywh_px_1080": [x0 + x, y0 + y, w, h],
            }
        )
    return sorted(rows, key=lambda row: (-row["area_px2"], row["centroid_px_1080"]))
