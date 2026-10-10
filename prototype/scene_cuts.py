"""Conservative hard-cut evidence at the tracker sampling resolution.

This intentionally catches only obvious edits. A missed cut remains possible;
an ordinary pan should not be treated as a proven identity boundary.
"""

import cv2
import numpy as np


def scene_cut_evidence(before, after, *, min_gray_change=45, min_hist_distance=0.35):
    if before.shape != after.shape or before.ndim != 3 or before.shape[2] != 3:
        raise ValueError("Expected matching BGR video frames")
    metrics = []
    for frame in (before, after):
        small = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [18, 8], [0, 180, 0, 256])
        cv2.normalize(hist, hist)
        metrics.append((gray, hist))
    gray_change = float(np.mean(cv2.absdiff(metrics[0][0], metrics[1][0])))
    hist_distance = float(cv2.compareHist(metrics[0][1], metrics[1][1], cv2.HISTCMP_BHATTACHARYYA))
    return {
        "gray_change": round(gray_change, 3),
        "hist_distance": round(hist_distance, 4),
        "hard_cut": gray_change >= min_gray_change and hist_distance >= min_hist_distance,
    }


def split_points_at_cuts(points, cut_times_s):
    """Do not retain a single object identity on both sides of a hard edit."""
    if not points:
        return []
    cuts = sorted(cut_times_s)
    segments = [[points[0]]]
    cut_index = 0
    for previous, point in zip(points, points[1:]):
        if point["time_s"] <= previous["time_s"]:
            raise ValueError("Track observations must increase in time")
        while cut_index < len(cuts) and cuts[cut_index] <= previous["time_s"]:
            cut_index += 1
        if cut_index < len(cuts) and cuts[cut_index] <= point["time_s"]:
            segments.append([])
        segments[-1].append(point)
    return segments
