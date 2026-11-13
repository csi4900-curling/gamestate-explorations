"""Development-only image ellipse for the split-screen receiving house."""

from statistics import median

import cv2
import numpy as np

from split_house_reference import right_house_paint_mask


def fit_house_ellipse(frame):
    mask = right_house_paint_mask(frame)
    contours, _ = cv2.findContours(mask * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    parts = []
    for contour in contours:
        _, y, width, height = cv2.boundingRect(contour)
        if width >= 50 and height >= 12 and 130 <= y <= 190 and cv2.contourArea(contour) >= 250:
            parts.append(contour)
    if not parts:
        return None
    points = np.concatenate(parts)
    if len(points) < 5 or cv2.boundingRect(points)[2] < 240:
        return None
    center, axes, angle = cv2.fitEllipse(points)
    major, minor = sorted((float(value) for value in axes), reverse=True)
    if not (
        430 <= center[0] <= 530
        and 140 <= center[1] <= 200
        and 220 <= major <= 320
        and 18 <= minor <= 65
        and abs(float(angle) - 90) <= 10
    ):
        return None
    return {
        "center_px": [round(float(center[0]), 3), round(float(center[1]), 3)],
        "axis_lengths_px": [round(major, 3), round(minor, 3)],
        "angle_degrees_opencv": round(float(angle), 3),
        "paint_component_count": len(parts),
        "coordinate_status": "image_paint_ellipse_not_metric_rink_geometry",
    }


def stable_house_ellipse(ellipses):
    """Use a three-sample median only when all frames agree geometrically."""
    if len(ellipses) != 3 or any(item is None for item in ellipses):
        return None, "abstain_missing_house_ellipse"
    values = [
        [
            item["center_px"][0],
            item["center_px"][1],
            item["axis_lengths_px"][0],
            item["axis_lengths_px"][1],
            item["angle_degrees_opencv"],
        ]
        for item in ellipses
    ]
    medians = [median(row[index] for row in values) for index in range(5)]
    limits = [5, 5, 12, 5, 5]
    if any(
        max(abs(row[index] - medians[index]) for row in values) > limit
        for index, limit in enumerate(limits)
    ):
        return None, "abstain_house_ellipse_changes_across_samples"
    return {
        "center_px": medians[:2],
        "axis_lengths_px": medians[2:4],
        "angle_degrees_opencv": medians[4],
        "coordinate_status": "stable_image_paint_ellipse_not_metric_rink_geometry",
    }, "stable_image_paint_ellipse"


def normalized_cap_image_xy(ellipse, pixel):
    """Normalize a *cap pixel*, not a stone contact point, by image ellipse axes."""
    cx, cy = ellipse["center_px"]
    major, minor = ellipse["axis_lengths_px"]
    return [round((pixel[0] - cx) / (major / 2), 4), round((pixel[1] - cy) / (minor / 2), 4)]
