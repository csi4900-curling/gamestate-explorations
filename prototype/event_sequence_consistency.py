"""Surface chronology conflicts without inventing missing throws or ends."""

from collections import Counter


def audit_sequence(events, coverage_gaps, *, nearby_s=40.0):
    """Return same-colour adjacency requiring source review.

    Alternation applies within an end. Without verified end boundaries or
    redelivery evidence, a same-colour pair is only a diagnostic.
    """
    if nearby_s <= 0:
        raise ValueError("Nearby threshold must be positive")
    ordered = sorted(events, key=lambda row: row["crossing_time_s"])
    if len({row["id"] for row in ordered}) != len(ordered):
        raise ValueError("Duplicate event ID")
    rows = []
    for previous, current in zip(ordered, ordered[1:]):
        start = previous["crossing_time_s"]
        end = current["crossing_time_s"]
        if end <= start:
            raise ValueError("Events share or reverse a timestamp")
        if previous["colour"] is None or previous["colour"] != current["colour"]:
            continue
        crossed_gaps = [gap for gap in coverage_gaps if max(gap[0], start) < min(gap[1], end)]
        same_run = previous.get("source_run_id") == current.get("source_run_id")
        rows.append(
            {
                "previous_event_id": previous["id"],
                "current_event_id": current["id"],
                "colour": current["colour"],
                "previous_time_s": start,
                "current_time_s": end,
                "separation_s": round(end - start, 3),
                "same_supported_run": same_run,
                "crossed_coverage_gaps_s": crossed_gaps,
                "nearby_review_priority": same_run and not crossed_gaps and end - start < nearby_s,
            }
        )
    return rows


def audit_end_sequence(events, boundary_times_s, coverage_gaps=()):
    """Summarize candidates within verified end intervals, without editing them.

    ``boundary_times_s`` must be source-reviewed moments between ends, rather
    than boundaries inferred from the candidate sequence being checked. An
    over-capacity colour or same-colour adjacency is a review clue only.
    """
    boundaries = list(boundary_times_s)
    if any(right <= left for left, right in zip(boundaries, boundaries[1:])):
        raise ValueError("End boundaries must be strictly increasing")
    ordered = sorted(events, key=lambda row: row["crossing_time_s"])
    if len({row["id"] for row in ordered}) != len(ordered):
        raise ValueError("Duplicate event ID")
    if any(
        right["crossing_time_s"] <= left["crossing_time_s"]
        for left, right in zip(ordered, ordered[1:])
    ):
        raise ValueError("Events share or reverse a timestamp")
    sections = [[] for _ in range(len(boundaries) + 1)]
    end_index = 0
    for event in ordered:
        time_s = event["crossing_time_s"]
        while end_index < len(boundaries) and time_s > boundaries[end_index]:
            end_index += 1
        if end_index < len(boundaries) and time_s == boundaries[end_index]:
            raise ValueError("Event lies on an end boundary")
        sections[end_index].append(event)
    rows = []
    for index, section in enumerate(sections):
        counts = Counter(event["colour"] for event in section)
        same_colour = audit_sequence(section, coverage_gaps)
        rows.append(
            {
                "end": index + 1,
                "first_event_id": section[0]["id"] if section else None,
                "last_event_id": section[-1]["id"] if section else None,
                "candidate_count": len(section),
                "candidate_colour_counts": {colour: counts[colour] for colour in ("red", "yellow")},
                "colour_capacity_excess": {
                    colour: max(0, counts[colour] - 8) for colour in ("red", "yellow")
                },
                "same_colour_pairs": [
                    {
                        "previous_event_id": row["previous_event_id"],
                        "current_event_id": row["current_event_id"],
                    }
                    for row in same_colour
                ],
            }
        )
    return rows
