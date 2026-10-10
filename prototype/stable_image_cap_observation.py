"""Repeatable image-space colour caps; no physical board interpretation."""

from math import dist
from statistics import median


def stable_cap_centers(frames, *, max_center_shift_px=12):
    if len(frames) < 3:
        raise ValueError("At least three frames required")
    times = [row["source_time_s"] for row in frames]
    if times != sorted(set(times)):
        raise ValueError("Frames must have unique increasing source times")
    tracks = [[cap] for cap in frames[0]["caps"]]
    for frame_index, frame in enumerate(frames[1:], 1):
        used = set()
        for track in tracks:
            if len(track) != frame_index:
                # A track missing a frame is no longer a complete stable sample.
                continue
            prev = track[-1]
            choices = [(dist(prev["pixel_center"], cap["pixel_center"]), i)
                       for i, cap in enumerate(frame["caps"])
                       if i not in used and cap["colour"] == prev["colour"]]
            if choices:
                distance, index = min(choices)
                if distance <= max_center_shift_px:
                    track.append(frame["caps"][index])
                    used.add(index)
    stable = []
    for track in tracks:
        if len(track) != len(frames):
            continue
        centre = [median(cap["pixel_center"][axis] for cap in track)
                  for axis in (0, 1)]
        spread = max(dist(cap["pixel_center"], centre) for cap in track)
        if spread > max_center_shift_px:
            continue
        stable.append({"colour": track[0]["colour"],
                       "median_pixel_center": centre,
                       "max_center_shift_px": round(spread, 3),
                       "supporting_times_s": times,
                       "physical_stone_identity": None})
    return sorted(stable, key=lambda row: (row["colour"],
                                           row["median_pixel_center"][0]))
