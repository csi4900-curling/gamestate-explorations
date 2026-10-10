"""Represent broadcast shots as temporal units between observed hard cuts."""


def shot_intervals(start_s, end_s, cut_times_s):
    if end_s <= start_s:
        raise ValueError("Invalid source interval")
    cuts = sorted(cut_times_s)
    if len(set(cuts)) != len(cuts) or any(not start_s < t < end_s for t in cuts):
        raise ValueError("Cuts must be unique and strictly inside the source interval")
    boundaries = [start_s, *cuts, end_s]
    return [[a, b] for a, b in zip(boundaries, boundaries[1:])]


def shot_for_time(intervals, t):
    hits = [index for index, (start, end) in enumerate(intervals)
            if start <= t < end]
    if len(hits) != 1:
        raise ValueError("Time outside or multiply covered by shot intervals")
    return hits[0]
