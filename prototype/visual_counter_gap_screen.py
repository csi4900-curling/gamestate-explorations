"""Screen visual-only proposals against ordered broadcast counter states."""

from bisect import bisect_right
from collections import Counter


COLOUR_INDEX = {"red": 0, "yellow": 1}


def _overlap(a, b):
    return max(a[0], b[0]) < min(a[1], b[1])


def screen_visual_counter_gaps(events, counter_events):
    """Report source-counter consistency without declaring physical truth."""
    times = [row["crossing_time_s"] for row in counter_events]
    ids = [row["id"] for row in counter_events]
    if times != sorted(set(times)) or len(ids) != len(set(ids)):
        raise ValueError("Counter events must have unique IDs and ordered times")
    for row in counter_events:
        delta = [a - b for a, b in zip(row["remaining_before"],
                                       row["remaining_after"])]
        if delta != ([1, 0] if row["colour"] == "red" else [0, 1]):
            raise ValueError(f"Counter colour and state disagree: {row['id']}")
    rows = []
    for event in events:
        if event["counter_id"] is not None:
            continue
        start, end = event["release_window_s"]
        colour = event["colour"]
        if not start < end or colour not in (None, "red", "yellow"):
            raise ValueError("Invalid visual-only event window or colour")
        index = bisect_right(times, start)
        left = counter_events[index - 1] if index else None
        right = counter_events[index] if index < len(counter_events) else None
        overlapping = [row for row in counter_events
                       if _overlap([start, end], row["evidence_interval_s"])
                       and (colour is None or row["colour"] == colour)]
        if overlapping:
            status = "overlaps_compatible_counter_evidence"
        elif colour is None:
            status = "candidate_colour_unresolved"
        elif left is None or right is None:
            status = "outside_two_counter_anchors"
        elif not (left["crossing_time_s"] <= start and
                  end <= right["evidence_interval_s"][0]):
            status = "counter_timing_overlaps_or_is_uncertain"
        else:
            before = left["remaining_after"]
            after = right["remaining_before"]
            colour_index = COLOUR_INDEX[colour]
            if before == after:
                status = "continuous_state_no_intervening_decrement"
            elif before[colour_index] > after[colour_index]:
                status = "state_gap_could_contain_colour_decrement"
            else:
                status = "counter_state_gap_or_reset"
        rows.append({
            "candidate_id": event["candidate_id"],
            "release_window_s": event["release_window_s"],
            "candidate_colour": colour,
            "preceding_counter_id": left["id"] if left else None,
            "following_counter_id": right["id"] if right else None,
            "overlapping_compatible_counter_ids": [row["id"] for row in overlapping],
            "status": status,
            "physical_throw_verified": False,
            "hard_reject": False,
        })
    return {"candidate_count": len(rows),
            "status_counts": dict(Counter(row["status"] for row in rows)),
            "rows": rows,
            "limitations": [
                "Broadcast counter updates can be delayed, missed, or misread.",
                "A stable counter state is contradictory source evidence, not independent proof of no throw.",
                "Overlapping counter evidence can indicate the same throw but does not prove identity.",
                "All visual-only proposals remain available for downstream review.",
            ]}
