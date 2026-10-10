"""Summarize raw cap evidence near a player before a broadcast handoff.

This is local visual evidence in a known delivery-side layout. The cue does
not identify a physical release or link the same stone across a cut.
"""

from math import dist
from statistics import median

from short_cap_transit import short_transits


def central_corridor(side):
    if side == "right":
        return 300, 450
    if side == "left":
        return 190, 340
    raise ValueError("Known delivery side required")


def central_cap_candidates(scored, side, *, minimum_score=-2.0):
    """Keep caps near the held/release location before the side-specific line."""
    x_min, x_max = central_corridor(side)
    return [row for row in scored if x_min <= row["pixel"][0] <= x_max
            and 280 <= row["pixel"][1] < 350
            and row["patch_score"] >= minimum_score]


def _tracks(observations, *, max_gap_s=0.8, max_speed_px_s=300):
    tracks = []
    for time_s, candidates in observations:
        used = set()
        for candidate in candidates:
            choices = []
            for index, track in enumerate(tracks):
                if index in used:
                    continue
                gap = time_s - track[-1]["time_s"]
                if not 0 < gap <= max_gap_s:
                    continue
                distance = dist(candidate["pixel"], track[-1]["pixel"])
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
    return tracks


def _held_runs(points, *, radius_px=8, min_duration_s=1.0, min_points=5):
    runs = []
    for start in range(len(points)):
        anchor = points[start]["pixel"]
        for end in range(start + 1, len(points)):
            if dist(anchor, points[end]["pixel"]) > radius_px:
                break
            span = points[end]["time_s"] - points[start]["time_s"]
            if end - start + 1 >= min_points and span >= min_duration_s:
                runs.append({"interval_s": [points[start]["time_s"],
                                             points[end]["time_s"]],
                             "point_count": end - start + 1,
                             "duration_s": round(span, 3),
                             "center_px": [round(median(p["pixel"][0]
                                                         for p in points[start:end + 1]), 2),
                                           round(median(p["pixel"][1]
                                                         for p in points[start:end + 1]), 2)],
                             "median_patch_score": round(median(p["patch_score"]
                                                               for p in points[start:end + 1]), 3)})
    return runs


def summarize_held_origin(observations):
    """Return strongest held and brief-moving evidence for each cap colour."""
    output = {}
    for colour in ("red", "yellow"):
        stream = [(t, [row for row in candidates if row["colour"] == colour])
                  for t, candidates in observations]
        tracks = _tracks(stream)
        holds = [hold for track in tracks for hold in _held_runs(track)]
        holds.sort(key=lambda row: (-row["duration_s"], -row["point_count"]))
        motion = short_transits(stream)
        output[colour] = {
            "candidate_count": sum(len(rows) for _, rows in stream),
            "track_count": len(tracks),
            "best_hold": holds[0] if holds else None,
            "best_motion": motion[0] if motion else None,
        }
    return output
