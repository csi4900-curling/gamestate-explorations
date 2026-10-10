"""Check whether camera registration is supported outside a target stone."""

import cv2
import numpy as np


def registration_support(before, after, *, exclude_bbox=None, margin_px=30):
    """Return similarity-fit support after excluding an optional target patch.

    This is a diagnostic, not a new camera transform used by the detector.
    A target-dominated fit is unsafe even if its reprojection error is small.
    """
    if before.shape != after.shape or before.shape[:2] != (360, 640):
        raise ValueError("Expected matching 640x360 BGR frames")
    gray_before = cv2.cvtColor(before, cv2.COLOR_BGR2GRAY)
    gray_after = cv2.cvtColor(after, cv2.COLOR_BGR2GRAY)
    mask = np.zeros(gray_before.shape, np.uint8)
    mask[70:, :] = 255
    if exclude_bbox is not None:
        x, y, width, height = exclude_bbox
        x0 = max(0, int(x - margin_px))
        y0 = max(70, int(y - margin_px))
        x1 = min(640, int(x + width + margin_px))
        y1 = min(360, int(y + height + margin_px))
        mask[y0:y1, x0:x1] = 0
    features = cv2.goodFeaturesToTrack(
        gray_before, maxCorners=700, qualityLevel=.01,
        minDistance=6, mask=mask)
    if features is None:
        return {"detected_features": 0, "tracked_features": 0, "inliers": 0,
                "inlier_fraction": 0, "inlier_bbox_px": None,
                "reliable_by_existing_rule": False}
    tracked, status, _ = cv2.calcOpticalFlowPyrLK(
        gray_before, gray_after, features, None, winSize=(21, 21), maxLevel=3)
    valid = status.ravel() == 1
    first = features[valid].reshape(-1, 2)
    second = tracked[valid].reshape(-1, 2)
    if len(first) < 10:
        return {"detected_features": len(features), "tracked_features": len(first),
                "inliers": 0, "inlier_fraction": 0, "inlier_bbox_px": None,
                "reliable_by_existing_rule": False}
    _, inlier_mask = cv2.estimateAffinePartial2D(
        first, second, method=cv2.RANSAC, ransacReprojThreshold=3)
    if inlier_mask is None:
        return {"detected_features": len(features), "tracked_features": len(first),
                "inliers": 0, "inlier_fraction": 0, "inlier_bbox_px": None,
                "reliable_by_existing_rule": False}
    inlier_points = first[inlier_mask.ravel() == 1]
    count = len(inlier_points)
    fraction = count / len(first)
    bounds = ([round(float(inlier_points[:, 0].min()), 2),
               round(float(inlier_points[:, 1].min()), 2),
               round(float(inlier_points[:, 0].max()), 2),
               round(float(inlier_points[:, 1].max()), 2)] if count else None)
    return {"detected_features": len(features),
            "tracked_features": len(first),
            "inliers": count,
            "inlier_fraction": round(fraction, 4),
            "inlier_bbox_px": bounds,
            "reliable_by_existing_rule": count >= 30 and fraction >= .25}
