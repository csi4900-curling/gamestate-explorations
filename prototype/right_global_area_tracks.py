"""Development-only global frame assignment for coloured 2024 right tracks."""

from math import hypot, log

import numpy as np
from scipy.optimize import linear_sum_assignment


def global_area_tracks(observations, *, max_gap_s=2, max_step_px=40,
                       area_weight_px=15, min_points=3, min_duration_s=2,
                       min_span_px=25):
    tracks = []
    for time_s, candidates in observations:
        active = [track for track in tracks
                  if 0 < time_s - track[-1]["time_s"] <= max_gap_s]
        used = set()
        if active and candidates:
            count = len(active)
            costs = np.full((count, len(candidates) + count), 1e6, dtype=float)
            for row, track in enumerate(active):
                previous = track[-1]
                gap = time_s - previous["time_s"]
                costs[row, len(candidates) + row] = 1000.0
                for col, candidate in enumerate(candidates):
                    distance = hypot(
                        candidate["pixel"][0] - previous["pixel"][0],
                        candidate["pixel"][1] - previous["pixel"][1])
                    if distance > max_step_px * gap:
                        continue
                    area_change = abs(log((candidate["cap_area_px2"] + 1) /
                                          (previous["cap_area_px2"] + 1)))
                    costs[row, col] = distance + area_weight_px * area_change
            rows, cols = linear_sum_assignment(costs)
            for row, col in zip(rows, cols):
                if col < len(candidates) and costs[row, col] < 1000:
                    active[row].append({**candidates[col], "time_s": time_s})
                    used.add(col)
        for col, candidate in enumerate(candidates):
            if col not in used:
                tracks.append([{**candidate, "time_s": time_s}])
    supported = []
    for points in tracks:
        if (len(points) < min_points or
                points[-1]["time_s"] - points[0]["time_s"] < min_duration_s):
            continue
        x0, y0 = points[0]["pixel"]
        span = max(hypot(point["pixel"][0] - x0,
                         point["pixel"][1] - y0) for point in points)
        if span >= min_span_px:
            supported.append({"points": points, "span_px": span})
    return sorted(supported, key=lambda row: (-len(row["points"]),
                                               -row["span_px"]))
