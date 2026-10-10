"""Cluster repeated video stone observations into a stable partial board."""

from math import dist
from statistics import median


def stable_board_stones(observations, *, max_pair_distance=0.10,
                        min_distinct_frames=3, min_span_s=4):
    """Return only same-colour positions repeatedly seen at nearly one place.

    `observations` is a sequence of frame rows with `time_s` and `stones`.
    Each stone has canonical lateral and longitudinal house-radius coordinates.
    Output stones remain anonymous; the caller must retain the source frames.
    """
    tracks = []
    for frame in sorted(observations, key=lambda row: row["time_s"]):
        used = set()
        for stone in frame["stones"]:
            xy = (stone["canonical_lateral_house_radii"],
                  stone["longitudinal_house_radii"])
            choices = []
            for index, track in enumerate(tracks):
                if index in used or track["colour"] != stone["colour"]:
                    continue
                center = (median(item[0] for item in track["positions"]),
                          median(item[1] for item in track["positions"]))
                distance = dist(xy, center)
                if distance <= max_pair_distance:
                    choices.append((distance, index))
            if choices:
                _, index = min(choices)
                track = tracks[index]
            else:
                index = len(tracks)
                track = {"colour": stone["colour"], "positions": [], "times": []}
                tracks.append(track)
            used.add(index)
            track["positions"].append(xy)
            track["times"].append(frame["time_s"])
    stable = []
    for track in tracks:
        times = track["times"]
        if len(set(times)) < min_distinct_frames or max(times) - min(times) < min_span_s:
            continue
        center = (median(item[0] for item in track["positions"]),
                  median(item[1] for item in track["positions"]))
        spread = max(dist(item, center) for item in track["positions"])
        if spread > max_pair_distance:
            continue
        stable.append({"colour": track["colour"],
                       "canonical_lateral_house_radii": round(center[0], 4),
                       "longitudinal_house_radii": round(center[1], 4),
                       "supporting_frame_count": len(set(times)),
                       "first_seen_s": min(times), "last_seen_s": max(times),
                       "max_position_spread_house_radii": round(spread, 4)})
    return sorted(stable, key=lambda row: (row["colour"],
                                           row["longitudinal_house_radii"],
                                           row["canonical_lateral_house_radii"]))
