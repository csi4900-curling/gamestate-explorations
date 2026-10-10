"""Development-only colour-track association with cap-size continuity."""

from math import hypot, log


def area_aware_tracks(observations, *, max_gap_s=1, max_step_px=40,
                      area_weight_px=15, min_points=3, min_duration_s=2,
                      min_span_px=25):
    tracks = []
    for time_s, candidates in observations:
        used = set()
        for track in tracks:
            previous = track[-1]
            gap = time_s - previous["time_s"]
            if not 0 < gap <= max_gap_s:
                continue
            choices = []
            for index, candidate in enumerate(candidates):
                if index in used:
                    continue
                distance = hypot(candidate["pixel"][0] - previous["pixel"][0],
                                 candidate["pixel"][1] - previous["pixel"][1])
                if distance > max_step_px * gap:
                    continue
                area_change = abs(log((candidate["cap_area_px2"] + 1) /
                                      (previous["cap_area_px2"] + 1)))
                choices.append((distance + area_weight_px * area_change,
                                distance, index))
            if choices:
                _, _, index = min(choices)
                track.append({**candidates[index], "time_s": time_s})
                used.add(index)
        for index, candidate in enumerate(candidates):
            if index not in used:
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
