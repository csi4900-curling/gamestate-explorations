"""Replay frozen short-cap transits while retaining their actual linked points.

This diagnostic copy preserves the original short_transits output and does not
change its frozen production implementation or prior artifacts.
"""

import numpy as np


def short_transits_with_points(
    observations,
    *,
    max_gap_s=0.65,
    max_speed_px_s=260,
    min_points=3,
    min_duration_s=0.4,
    min_displacement_px=30,
    max_path_ratio=1.8,
):
    tracks = []
    previous_time = None
    for time_s, candidates in observations:
        if previous_time is not None and time_s <= previous_time:
            raise ValueError("Observation times must increase")
        previous_time = time_s
        used = set()
        for candidate in candidates:
            position = np.asarray(candidate["pixel"], dtype=float)
            choices = []
            for index, track in enumerate(tracks):
                if index in used:
                    continue
                gap = time_s - track[-1]["time_s"]
                if not 0 < gap <= max_gap_s:
                    continue
                previous = np.asarray(track[-1]["pixel"], dtype=float)
                distance = float(np.linalg.norm(position - previous))
                if distance <= max_speed_px_s * gap:
                    choices.append((distance, index))
            point = dict(candidate, time_s=time_s)
            if choices:
                _, index = min(choices)
                tracks[index].append(point)
                used.add(index)
            else:
                tracks.append([point])
                used.add(len(tracks) - 1)
    result = []
    for points in tracks:
        if len(points) < min_points:
            continue
        duration = points[-1]["time_s"] - points[0]["time_s"]
        if duration < min_duration_s:
            continue
        positions = np.asarray([row["pixel"] for row in points], dtype=float)
        steps = np.linalg.norm(np.diff(positions, axis=0), axis=1)
        displacement = float(np.linalg.norm(positions[-1] - positions[0]))
        length = float(steps.sum())
        if displacement < min_displacement_px or length > max_path_ratio * displacement:
            continue
        summary = {
            "interval_s": [points[0]["time_s"], points[-1]["time_s"]],
            "point_count": len(points),
            "first_pixel": points[0]["pixel"],
            "last_pixel": points[-1]["pixel"],
            "displacement_px": round(displacement, 2),
            "path_ratio": round(length / displacement, 3),
            "median_patch_score": round(float(np.median([p["patch_score"] for p in points])), 3),
        }
        result.append((summary, points))
    return sorted(result, key=lambda row: (-row[0]["point_count"], -row[0]["displacement_px"]))
