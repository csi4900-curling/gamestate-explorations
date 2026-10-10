"""Conservative stable-stone observations after a provisional receiving path."""

from math import dist, isfinite
from statistics import median


def tail_bounds(path_last_s, crossing_s, next_candidate_s, source_end_s, *,
                max_after_crossing_s=35.0, next_guard_s=1.0,
                min_tail_s=4.0):
    """Stop before the next passage candidate, even if that candidate is false."""
    if not all(isfinite(v) for v in (path_last_s, crossing_s, source_end_s)):
        raise ValueError("Nonfinite event time")
    if next_candidate_s is not None and not isfinite(next_candidate_s):
        raise ValueError("Nonfinite next-candidate time")
    start = path_last_s + 0.5
    stop = min(source_end_s, crossing_s + max_after_crossing_s,
               next_candidate_s - next_guard_s if next_candidate_s is not None
               else source_end_s)
    return {"start_s": start, "stop_s": stop,
            "eligible": stop - start >= min_tail_s,
            "reason": ("bounded_quiet_tail" if stop - start >= min_tail_s else
                       "insufficient_time_before_next_candidate_or_interval_end")}


def stable_view_local_stones(frames, *, max_pair_distance_m=0.18,
                             min_distinct_frames=3, min_span_s=4.0,
                             max_endpoint_age_s=2.0,
                             use_stable_suffix=False):
    """Cluster repeatedly visible stones; never assert board completeness."""
    accepted = [frame for frame in frames if frame["status"] == "registered"]
    if not accepted:
        return {"status": "no_registered_tail_frames", "stones": [],
                "last_registered_s": None}
    times = [float(frame["source_time_s"]) for frame in accepted]
    if any(not isfinite(t) for t in times) or any(a >= b for a, b in zip(times, times[1:])):
        raise ValueError("Tail frames must have increasing finite times")
    last = times[-1]
    if last - times[0] < min_span_s:
        return {"status": "insufficient_registered_tail_span", "stones": [],
                "last_registered_s": last}
    tracks = []
    for frame in accepted:
        used = set()
        for stone in frame["stones"]:
            colour = stone["colour"]
            xy = tuple(map(float, stone["view_local_ground_position_m"]))
            if colour not in ("red", "yellow") or len(xy) != 2 or (
                    not all(isfinite(value) for value in xy)):
                raise ValueError("Invalid stone proposal")
            choices = []
            for index, track in enumerate(tracks):
                if index in used or track["colour"] != colour:
                    continue
                center = (median(p[0] for p in track["positions"]),
                          median(p[1] for p in track["positions"]))
                distance = dist(xy, center)
                if distance <= max_pair_distance_m:
                    choices.append((distance, index))
            if choices:
                _, index = min(choices)
                track = tracks[index]
            else:
                index = len(tracks)
                track = {"colour": colour, "positions": [], "times": []}
                tracks.append(track)
            used.add(index)
            track["positions"].append(xy)
            track["times"].append(frame["source_time_s"])
    stable = []
    for track in tracks:
        positions = track["positions"]
        times = track["times"]
        dropped_earlier = 0
        if use_stable_suffix:
            for start in range(len(times)):
                later_positions = positions[start:]
                later_times = times[start:]
                if (len(set(later_times)) < min_distinct_frames or
                        max(later_times) - min(later_times) < min_span_s or
                        last - max(later_times) > max_endpoint_age_s):
                    continue
                center = (median(p[0] for p in later_positions),
                          median(p[1] for p in later_positions))
                spread = max(dist(point, center) for point in later_positions)
                if spread <= max_pair_distance_m:
                    positions, times = later_positions, later_times
                    dropped_earlier = start
                    break
        if (len(set(times)) < min_distinct_frames or
                max(times) - min(times) < min_span_s or
                last - max(times) > max_endpoint_age_s):
            continue
        center = (median(p[0] for p in positions),
                  median(p[1] for p in positions))
        spread = max(dist(point, center) for point in positions)
        if spread > max_pair_distance_m:
            continue
        stable.append({"colour": track["colour"],
                       "view_local_ground_position_m": list(center),
                       "first_seen_s": min(times),
                       "last_seen_s": max(times),
                       "supporting_frame_count": len(set(times)),
                       "max_position_spread_m": spread,
                       "persistent_stone_identity": None})
        if use_stable_suffix:
            stable[-1]["discarded_earlier_observations"] = dropped_earlier
    stable.sort(key=lambda row: (row["colour"],
                                 row["view_local_ground_position_m"][1],
                                 row["view_local_ground_position_m"][0]))
    for index, stone in enumerate(stable, 1):
        stone["local_observation_id"] = f"V{index:02d}"
    return {"status": ("partial_stable_view_local_board" if stable else
                       "no_stable_stones_in_registered_tail"),
            "stones": stable, "last_registered_s": last}
