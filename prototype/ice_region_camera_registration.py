"""Register camera motion using only a broad ice-like source-image region.

This mask is a source-pixel heuristic. It is not a calibrated rink plane.
"""

import cv2
import numpy as np


def largest_ice_like_region(frame, *, min_fraction=0.20):
    if frame.shape[:2] != (360, 640):
        raise ValueError("Expected 640x360 source frame")
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    white = (((hsv[:, :, 1] < 90) & (hsv[:, :, 2] > 150))
             .astype(np.uint8) * 255)
    white[:70] = 0
    closed = cv2.morphologyEx(white, cv2.MORPH_CLOSE,
                             np.ones((41, 41), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(closed)
    if count < 2:
        return None, 0.0
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    fraction = float(stats[largest, cv2.CC_STAT_AREA] / (640 * 360))
    return ((labels == largest).astype(np.uint8) * 255
            if fraction >= min_fraction else None), fraction


def estimate_ice_region_transform(before, after, target_pixel,
                                  *, exclusion_radius_px=30):
    if before.shape != after.shape or before.shape[:2] != (360, 640):
        raise ValueError("Expected matching 640x360 source frames")
    mask, fraction = largest_ice_like_region(before)
    if mask is None:
        return {"status": "no_broad_ice_like_region",
                "region_fraction": round(fraction, 4),
                "tracked_features": 0, "inliers": 0,
                "inlier_fraction": 0.0, "matrix": None}
    x, y = map(round, target_pixel)
    r = exclusion_radius_px
    mask[max(0, y-r):min(360, y+r), max(0, x-r):min(640, x+r)] = 0
    gray_before = cv2.cvtColor(before, cv2.COLOR_BGR2GRAY)
    gray_after = cv2.cvtColor(after, cv2.COLOR_BGR2GRAY)
    features = cv2.goodFeaturesToTrack(
        gray_before, maxCorners=700, qualityLevel=0.01,
        minDistance=6, mask=mask)
    if features is None or len(features) < 10:
        return {"status": "insufficient_region_features",
                "region_fraction": round(fraction, 4),
                "tracked_features": 0 if features is None else len(features),
                "inliers": 0, "inlier_fraction": 0.0, "matrix": None}
    tracked, status, _ = cv2.calcOpticalFlowPyrLK(
        gray_before, gray_after, features, None,
        winSize=(21, 21), maxLevel=3)
    valid = status.ravel() == 1
    first = features[valid].reshape(-1, 2)
    second = tracked[valid].reshape(-1, 2)
    if len(first) < 10:
        return {"status": "insufficient_tracked_features",
                "region_fraction": round(fraction, 4),
                "tracked_features": len(first), "inliers": 0,
                "inlier_fraction": 0.0, "matrix": None}
    matrix, inliers = cv2.estimateAffinePartial2D(
        first, second, method=cv2.RANSAC, ransacReprojThreshold=3)
    if matrix is None or inliers is None:
        return {"status": "affine_fit_failed",
                "region_fraction": round(fraction, 4),
                "tracked_features": len(first), "inliers": 0,
                "inlier_fraction": 0.0, "matrix": None}
    count = int(inliers.sum())
    inlier_fraction = count / len(first)
    reliable = count >= 30 and inlier_fraction >= 0.25
    return {"status": ("registered" if reliable else "unreliable_affine_fit"),
            "region_fraction": round(fraction, 4),
            "tracked_features": len(first),
            "inliers": count,
            "inlier_fraction": round(inlier_fraction, 4),
            "matrix": matrix if reliable else None}


def ice_region_composed_residual(before_pixel, after_pixel, before_time_s,
                                 after_time_s, frame_at,
                                 *, nominal_step_s=0.25):
    if after_time_s <= before_time_s or nominal_step_s <= 0:
        raise ValueError("Invalid source-frame interval")
    interval = after_time_s - before_time_s
    steps = max(1, round(interval / nominal_step_s))
    times = [before_time_s + interval * index / steps
             for index in range(steps + 1)]
    composed = np.eye(3)
    details = []
    frame = frame_at(times[0])
    for index, time in enumerate(times[1:]):
        next_frame = frame_at(time)
        fraction = index / steps
        target = np.asarray(before_pixel) + fraction * (
            np.asarray(after_pixel) - np.asarray(before_pixel))
        fit = estimate_ice_region_transform(frame, next_frame, target)
        details.append({
            "interval_s": [round(times[index], 4), round(time, 4)],
            "status": fit["status"],
            "region_fraction": fit["region_fraction"],
            "tracked_features": fit["tracked_features"],
            "inliers": fit["inliers"],
            "inlier_fraction": fit["inlier_fraction"],
        })
        if fit["matrix"] is None:
            return {"status": "unregistered_subpair",
                    "camera_residual_px": None,
                    "subpairs": details}
        transform = np.eye(3)
        transform[:2] = fit["matrix"]
        composed = transform @ composed
        frame = next_frame
    projected = composed @ np.asarray([*before_pixel, 1], dtype=float)
    residual = np.linalg.norm(np.asarray(after_pixel, dtype=float) - projected[:2])
    return {"status": "all_ice_region_subpairs_registered",
            "camera_residual_px": round(float(residual), 3),
            "subpairs": details}
