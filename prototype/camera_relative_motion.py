"""Measure candidate movement relative to registered rink/background pixels."""

import cv2
import numpy as np


def estimate_camera_transform(before, after):
    """Estimate a 2D similarity transform from non-overlay image features."""
    if before.shape != after.shape or before.shape[:2] != (360, 640):
        raise ValueError("Expected matching 640x360 BGR frames")
    gray_before = cv2.cvtColor(before, cv2.COLOR_BGR2GRAY)
    gray_after = cv2.cvtColor(after, cv2.COLOR_BGR2GRAY)
    mask = np.zeros(gray_before.shape, np.uint8)
    mask[70:, :] = 255
    features = cv2.goodFeaturesToTrack(
        gray_before, maxCorners=700, qualityLevel=0.01,
        minDistance=6, mask=mask,
    )
    if features is None or len(features) < 10:
        return None
    tracked, status, _ = cv2.calcOpticalFlowPyrLK(
        gray_before, gray_after, features, None,
        winSize=(21, 21), maxLevel=3,
    )
    valid = status.ravel() == 1
    first = features[valid].reshape(-1, 2)
    second = tracked[valid].reshape(-1, 2)
    if len(first) < 10:
        return None
    matrix, inliers = cv2.estimateAffinePartial2D(
        first, second, method=cv2.RANSAC, ransacReprojThreshold=3,
    )
    if matrix is None or inliers is None:
        return None
    inlier_count = int(inliers.sum())
    return {
        "matrix": matrix,
        "tracked_features": len(first),
        "inliers": inlier_count,
        "inlier_fraction": inlier_count / len(first),
        "reliable": inlier_count >= 30 and inlier_count / len(first) >= 0.25,
    }


def residual_motion(before_pixel, after_pixel, transform):
    """Return candidate displacement after removing estimated camera motion."""
    projected = transform["matrix"] @ np.asarray([*before_pixel, 1.0], dtype=float)
    return float(np.linalg.norm(np.asarray(after_pixel, dtype=float) - projected))


def sample_track_camera_motion(points, frame_at, *, step_s=1.2):
    """Sample approximately one-second pairs, retaining registration failures."""
    rows = []
    target = points[0]["time_s"]
    while target + 1 <= points[-1]["time_s"]:
        before = min(points, key=lambda row: abs(row["time_s"] - target))
        after = min(points, key=lambda row: abs(row["time_s"] - before["time_s"] - 1))
        if after["time_s"] <= before["time_s"] + 0.6:
            target = before["time_s"] + step_s
            continue
        start_pixel = before["pixel"]
        end_pixel = after["pixel"]
        inside = all(0 <= xy[0] < 640 and 0 <= xy[1] < 360
                     for xy in (start_pixel, end_pixel))
        registration = estimate_camera_transform(
            frame_at(before["time_s"]), frame_at(after["time_s"])
        )
        usable = bool(inside and registration is not None and registration["reliable"])
        rows.append({
            "interval_s": [before["time_s"], after["time_s"]],
            "raw_displacement_px": round(float(np.linalg.norm(
                np.subtract(end_pixel, start_pixel))), 3),
            "camera_residual_px": round(residual_motion(start_pixel, end_pixel, registration), 3)
            if usable else None,
            "track_points_inside_frame": inside,
            "tracked_features": registration["tracked_features"] if registration else 0,
            "inliers": registration["inliers"] if registration else 0,
            "inlier_fraction": round(registration["inlier_fraction"], 3)
            if registration else 0,
            "registration_reliable": usable,
        })
        target = before["time_s"] + step_s
    return rows


def longest_relative_motion_run(rows, *, min_residual_px=5, max_pair_gap_s=1.5):
    """Consecutive reliable moving pairs, without bridging cuts or bad fits."""
    longest = 0
    current = 0
    previous_start = None
    for row in rows:
        start = row["interval_s"][0]
        if (row["camera_residual_px"] is not None
                and row["camera_residual_px"] > min_residual_px
                and (previous_start is None or start - previous_start <= max_pair_gap_s)):
            current += 1
            longest = max(longest, current)
        else:
            current = 0
        previous_start = start
    return longest
