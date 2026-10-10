"""Yellow-handle contour proposals in a configurable right-panel ice region.

The thresholds reproduce the frozen contour probe; only the permitted search
region changes. A contour is an image observation, not a stone classification.
"""

import cv2


def yellow_contours_in_roi(frame, roi_1080p):
    image = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
    hue, saturation, value = cv2.split(cv2.cvtColor(image, cv2.COLOR_BGR2HSV))
    mask = (hue > 16) & (hue < 43) & (saturation > 60) & (value > 65)
    contours, _ = cv2.findContours(
        mask.astype("uint8") * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    x1, y1, x2, y2 = roi_1080p
    points = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)
        if area < 15 or w > 160 or h > 100:
            continue
        center = [3 * (x + w / 2), 3 * (y + h / 2) + 18]
        if not (x1 <= center[0] <= x2 and y1 <= center[1] <= y2):
            continue
        points.append(
            {
                "center_1080p_px": center,
                "handle_bbox_360p": [x, y, w, h],
                "handle_area_360p_px2": round(float(area), 2),
            }
        )
    return points
