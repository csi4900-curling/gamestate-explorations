"""Conservative stable colour-cap proposals in a fixed right-camera view."""

from math import dist, isfinite
from statistics import median


def stable_cap_candidates(frames, *, max_pair_distance_px=5.0):
    """Keep same-colour blobs seen at one image position in all three frames."""
    if len(frames) != 3:
        raise ValueError("Expected exactly three sampled source frames")
    times = [float(frame["time_s"]) for frame in frames]
    if any(not isfinite(t) for t in times) or not times[0] < times[1] < times[2]:
        raise ValueError("Frame times must increase and be finite")
    tracks = [
        {"colour": row["colour"], "points": [row["pixel"]], "areas": [row["cap_area_px2"]]}
        for row in frames[0]["cap_candidates"]
    ]
    for frame_index, frame in enumerate(frames[1:], 1):
        used = set()
        for row in frame["cap_candidates"]:
            choices = []
            for i, track in enumerate(tracks):
                if i in used or len(track["points"]) != frame_index:
                    continue
                if track["colour"] != row["colour"]:
                    continue
                center = [median(p[axis] for p in track["points"]) for axis in (0, 1)]
                separation = dist(center, row["pixel"])
                if separation <= max_pair_distance_px:
                    choices.append((separation, i))
            if choices:
                _, i = min(choices)
                used.add(i)
                tracks[i]["points"].append(row["pixel"])
                tracks[i]["areas"].append(row["cap_area_px2"])
    stable = []
    for track in tracks:
        if len(track["points"]) != 3:
            continue
        center = [median(p[axis] for p in track["points"]) for axis in (0, 1)]
        spread = max(dist(center, p) for p in track["points"])
        if spread > max_pair_distance_px:
            continue
        stable.append(
            {
                "colour": track["colour"],
                "pixel_center": [round(v, 2) for v in center],
                "sample_times_s": times,
                "supporting_frame_count": 3,
                "max_position_spread_px": round(spread, 2),
                "median_cap_area_px2": round(median(track["areas"]), 2),
                "physical_stone_identity_verified": False,
            }
        )
    stable.sort(key=lambda row: (row["colour"], row["pixel_center"][1], row["pixel_center"][0]))
    for i, row in enumerate(stable, 1):
        row["local_observation_id"] = f"C{i:02d}"
    return stable
