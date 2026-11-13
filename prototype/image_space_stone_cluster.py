"""Cluster repeated stone-like patches without inventing ice coordinates."""

from math import dist
from statistics import median


def stable_image_caps(frames, *, max_pair_distance_px=12, min_distinct_frames=3, min_span_s=4):
    """Return anonymous stable image-space cap observations."""
    tracks = []
    for frame in sorted(frames, key=lambda row: row["time_s"]):
        used = set()
        for candidate in frame["candidates"]:
            choices = []
            for index, track in enumerate(tracks):
                if index in used or track["colour"] != candidate["colour"]:
                    continue
                center = (
                    median(point["pixel"][0] for point in track["points"]),
                    median(point["pixel"][1] for point in track["points"]),
                )
                distance = dist(candidate["pixel"], center)
                if distance <= max_pair_distance_px:
                    choices.append((distance, index))
            point = {
                "time_s": frame["time_s"],
                "pixel": candidate["pixel"],
                "patch_score": candidate["patch_score"],
            }
            if choices:
                _, index = min(choices)
                track = tracks[index]
            else:
                index = len(tracks)
                track = {"colour": candidate["colour"], "points": []}
                tracks.append(track)
            track["points"].append(point)
            used.add(index)
    stable = []
    for track in tracks:
        points = track["points"]
        times = [point["time_s"] for point in points]
        if len(set(times)) < min_distinct_frames or max(times) - min(times) < min_span_s:
            continue
        center = (
            median(point["pixel"][0] for point in points),
            median(point["pixel"][1] for point in points),
        )
        spread = max(dist(point["pixel"], center) for point in points)
        if spread > max_pair_distance_px:
            continue
        stable.append(
            {
                "colour": track["colour"],
                "pixel_center": [round(center[0], 2), round(center[1], 2)],
                "first_seen_s": min(times),
                "last_seen_s": max(times),
                "supporting_frame_count": len(set(times)),
                "max_spread_px": round(spread, 2),
                "median_patch_score": round(median(point["patch_score"] for point in points), 3),
                "coordinate_frame": "image_pixels_640x360",
                "physical_stone_identity": None,
            }
        )
    return sorted(stable, key=lambda row: (row["colour"], row["pixel_center"][0]))
