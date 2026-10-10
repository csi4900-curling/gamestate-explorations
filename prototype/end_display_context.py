"""Attach local broadcast-display evidence to event candidates.

The displayed end can lag physical play. This module never assigns a physical
end, deletes a candidate, or treats a marker timestamp as a delivery time.
"""

from bisect import bisect_left


def annotate_display_context(events, samples, *, max_bracket_s=30.0,
                             ignored_marker_times_s=()):
    if max_bracket_s <= 0:
        raise ValueError("Maximum bracket distance must be positive")
    ignored = set(ignored_marker_times_s)
    hits = [(row["time_s"], row["marker"]["end"])
            for row in samples
            if row.get("marker") is not None and row["time_s"] not in ignored]
    if any(right[0] <= left[0] for left, right in zip(hits, hits[1:])):
        raise ValueError("Marker observations must have increasing times")
    times = [time_s for time_s, _ in hits]
    result = []
    for event in events:
        t = event["crossing_time_s"]
        index = bisect_left(times, t)
        left = hits[index - 1] if index else None
        right = hits[index] if index < len(hits) else None
        nearby_left = left if left and t - left[0] <= max_bracket_s else None
        nearby_right = right if right and right[0] - t <= max_bracket_s else None
        if nearby_left and nearby_right:
            if nearby_left[1] == nearby_right[1]:
                status = "bracketed_display_end"
                displayed_end = nearby_left[1]
            else:
                status = "bracketed_display_change"
                displayed_end = None
        else:
            status = "display_context_unknown"
            displayed_end = None
        result.append({
            "event_id": event["id"],
            "crossing_time_s": t,
            "display_context_status": status,
            "displayed_end": displayed_end,
            "left_marker": {"time_s": left[0], "end": left[1]} if left else None,
            "right_marker": {"time_s": right[0], "end": right[1]} if right else None,
            "physical_end": None,
        })
    return result
