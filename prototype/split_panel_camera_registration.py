"""Exploratory camera registration for one 2024 split-screen panel.

Coordinates are in a 640x720 aspect-preserving resize of a 960x1080 panel.
This adapts the 2022 ice-region method to a new image shape; it does not
modify the frozen 640x360 implementation or establish a rink homography.
"""

import cv2
import numpy as np


PANEL_WIDTH = 960
PANEL_HEIGHT = 1080
SCALE = 2 / 3
FRAME_SIZE = (640, 720)  # width, height


def panel_for_pixel(pixel):
    x, y = pixel
    if not (0 <= x < 2 * PANEL_WIDTH and 0 <= y < PANEL_HEIGHT):
        raise ValueError("Point outside 1920x1080 split-screen source")
    return 0 if x < PANEL_WIDTH else 1


def panel_pixel(pixel, panel):
    if panel not in (0, 1) or panel_for_pixel(pixel) != panel:
        raise ValueError("Point does not belong to selected panel")
    return ((pixel[0] - panel * PANEL_WIDTH) * SCALE, pixel[1] * SCALE)


def resize_panel(frame, panel):
    if frame.shape[:2] != (PANEL_HEIGHT, 2 * PANEL_WIDTH):
        raise ValueError("Expected 1920x1080 split-screen source frame")
    if panel not in (0, 1):
        raise ValueError("Unknown panel")
    crop = frame[:, panel * PANEL_WIDTH : (panel + 1) * PANEL_WIDTH]
    return cv2.resize(crop, FRAME_SIZE, interpolation=cv2.INTER_AREA)


def ice_region(frame):
    if frame.shape[:2] != (720, 640):
        raise ValueError("Expected 640x720 panel image")
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    white = ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] > 150)).astype(np.uint8) * 255
    # Same top-screen fraction as the frozen 2022 rule (70 / 360).
    white[:140] = 0
    closed = cv2.morphologyEx(white, cv2.MORPH_CLOSE, np.ones((41, 41), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(closed)
    if count < 2:
        return None, 0.0
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    fraction = float(stats[largest, cv2.CC_STAT_AREA] / (640 * 720))
    return ((labels == largest).astype(np.uint8) * 255 if fraction >= 0.20 else None), fraction


def edge_alignment_support(gray_before, gray_after, region_mask, matrix):
    """Compare a camera fit with the no-motion hypothesis on scene edges.

    The broad ice-like component is dilated to include painted rink lines at
    its boundary. A fit supported by moving people can have many LK inliers
    while misaligning these stable scene edges.
    """
    region = cv2.dilate(region_mask, np.ones((15, 15), np.uint8))
    before_edges = cv2.Canny(gray_before, 80, 180)
    after_edges = cv2.Canny(gray_after, 80, 180)
    yy, xx = np.where((before_edges > 0) & (region > 0))
    if len(xx) < 1000:
        return None
    # Deterministic bounded sampling avoids privileging one image quadrant.
    stride = max(1, len(xx) // 5000)
    xx, yy = xx[::stride], yy[::stride]
    points = np.column_stack((xx, yy, np.ones(len(xx))))
    projected = np.rint(points @ matrix.T).astype(int)
    inside = (
        (projected[:, 0] >= 0)
        & (projected[:, 0] < 640)
        & (projected[:, 1] >= 0)
        & (projected[:, 1] < 720)
    )
    distance = cv2.distanceTransform(255 - after_edges, cv2.DIST_L2, 3)
    identity_support = float(np.mean(distance[yy, xx] < 2))
    transformed_support = float(np.mean(distance[projected[inside, 1], projected[inside, 0]] < 2))
    return {
        "edge_sample_count": len(xx),
        "edge_identity_support": round(identity_support, 4),
        "edge_transform_support": round(transformed_support, 4),
    }


def estimate_transform(before, after, target_pixel):
    if before.shape != after.shape or before.shape[:2] != (720, 640):
        raise ValueError("Expected matching 640x720 panel images")
    mask, fraction = ice_region(before)
    result = {
        "region_fraction": round(fraction, 4),
        "tracked_features": 0,
        "inliers": 0,
        "inlier_fraction": 0.0,
        "matrix": None,
    }
    if mask is None:
        return {**result, "status": "no_broad_ice_like_region"}
    x, y = map(round, target_pixel)
    mask[max(0, y - 30) : min(720, y + 30), max(0, x - 30) : min(640, x + 30)] = 0
    gray_before = cv2.cvtColor(before, cv2.COLOR_BGR2GRAY)
    gray_after = cv2.cvtColor(after, cv2.COLOR_BGR2GRAY)
    features = cv2.goodFeaturesToTrack(
        gray_before, maxCorners=700, qualityLevel=0.01, minDistance=6, mask=mask
    )
    if features is None or len(features) < 10:
        result["tracked_features"] = 0 if features is None else len(features)
        return {**result, "status": "insufficient_region_features"}
    tracked, status, _ = cv2.calcOpticalFlowPyrLK(
        gray_before, gray_after, features, None, winSize=(21, 21), maxLevel=3
    )
    valid = status.ravel() == 1
    first = features[valid].reshape(-1, 2)
    second = tracked[valid].reshape(-1, 2)
    result["tracked_features"] = len(first)
    if len(first) < 10:
        return {**result, "status": "insufficient_tracked_features"}
    matrix, inliers = cv2.estimateAffinePartial2D(
        first, second, method=cv2.RANSAC, ransacReprojThreshold=3
    )
    if matrix is None or inliers is None:
        return {**result, "status": "affine_fit_failed"}
    count = int(inliers.sum())
    fraction = count / len(first)
    result.update(inliers=count, inlier_fraction=round(fraction, 4))
    if count < 30 or fraction < 0.25:
        return {**result, "status": "unreliable_affine_fit"}
    edge = edge_alignment_support(gray_before, gray_after, mask, matrix)
    if edge is not None:
        result.update(edge)
        projected_target = matrix @ np.asarray([x, y, 1.0])
        target_shift = np.linalg.norm(projected_target - np.asarray([x, y]))
        result["proposed_target_shift_px"] = round(float(target_shift), 3)
        if (
            target_shift > 3
            and edge["edge_identity_support"] > edge["edge_transform_support"] + 0.05
        ):
            return {**result, "status": "edge_alignment_contradicts_transform"}
        if (
            target_shift > 2
            and edge["edge_identity_support"] > 0.85
            and edge["edge_transform_support"] < edge["edge_identity_support"] + 0.03
        ):
            return {**result, "status": "high_identity_edge_support"}
    return {**result, "status": "registered", "matrix": matrix}


def camera_relative_pair(
    before_pixel, after_pixel, before_time_s, after_time_s, frame_at, *, nominal_step_s=0.25
):
    """Compose only successful short transforms and retain failure reasons."""
    if after_time_s <= before_time_s or nominal_step_s <= 0:
        raise ValueError("Invalid source-frame interval")
    steps = max(1, round((after_time_s - before_time_s) / nominal_step_s))
    times = np.linspace(before_time_s, after_time_s, steps + 1)
    composed = np.eye(3)
    details = []
    frame = frame_at(float(times[0]))
    for index in range(steps):
        next_frame = frame_at(float(times[index + 1]))
        target = np.asarray(before_pixel) + (index / steps) * (
            np.asarray(after_pixel) - np.asarray(before_pixel)
        )
        fit = estimate_transform(frame, next_frame, target)
        details.append(
            {
                "interval_s": [round(float(times[index]), 4), round(float(times[index + 1]), 4)],
                **{key: value for key, value in fit.items() if key != "matrix"},
            }
        )
        if fit["matrix"] is None:
            return {
                "status": "unregistered_subpair",
                "camera_residual_px": None,
                "subpairs": details,
            }
        matrix = np.eye(3)
        matrix[:2] = fit["matrix"]
        composed = matrix @ composed
        frame = next_frame
    projected = composed @ np.asarray([*before_pixel, 1], dtype=float)
    residual = np.linalg.norm(np.asarray(after_pixel) - projected[:2])
    return {
        "status": "all_ice_region_subpairs_registered",
        "camera_residual_px": round(float(residual), 3),
        "subpairs": details,
    }
