"""Image-space house paint reference for 2024 right-panel split views."""

import cv2
import numpy as np


def right_house_paint_mask(frame):
    if frame.shape != (360, 640, 3):
        raise ValueError("Expected 640x360 BGR source frame")
    hue, sat, value = cv2.split(cv2.cvtColor(frame, cv2.COLOR_BGR2HSV))
    mask = ((hue >= 65) & (hue <= 125) & (sat >= 35) & (value >= 100)).astype(np.uint8)
    mask[:120] = 0
    mask[210:] = 0
    mask[:, :340] = 0
    mask[:, 630:] = 0
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), dtype=np.uint8))


def fit_right_house_paint(frame):
    """Fit the visible ring envelope, including disconnected left/right halves."""
    mask = right_house_paint_mask(frame)
    contours, _ = cv2.findContours(mask * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    parts = []
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        if width >= 100 and height >= 15 and 130 <= y <= 170 and cv2.contourArea(contour) >= 300:
            parts.append(contour)
    if not parts:
        return None
    points = np.concatenate(parts, axis=0)
    x, y, width, height = cv2.boundingRect(points)
    if width < 240 or len(points) < 5:
        return None
    center, axes, angle = cv2.fitEllipse(points)
    minor, major = sorted(float(value) for value in axes)
    if not (
        430 <= center[0] <= 530
        and 140 <= center[1] <= 180
        and 220 <= major <= 320
        and 18 <= minor <= 65
    ):
        return None
    return {
        "center_px": [round(float(center[0]), 3), round(float(center[1]), 3)],
        "axis_lengths_px": [round(major, 3), round(minor, 3)],
        "angle_degrees_opencv": round(float(angle), 3),
        "component_bbox_px": [x, y, width, height],
        "paint_component_count": len(parts),
        "coordinate_status": "source_right_panel_image_ellipse_not_metric_rink_geometry",
    }
