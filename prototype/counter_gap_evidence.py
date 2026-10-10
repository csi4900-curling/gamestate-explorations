"""Locate counter updates in route gaps without asserting throw truth."""


def classify_counter_gap_events(counter_events, coverage_gaps):
    """Classify each counter event against unsupported route intervals.

    A fully interior evidence interval is useful gap evidence. A transition
    touching supported video needs boundary review because its update can lag
    the physical delivery.
    """
    gaps = sorted((float(start), float(end)) for start, end in coverage_gaps)
    if any(start >= end for start, end in gaps):
        raise ValueError("Coverage gaps must have positive duration")
    if any(previous[1] > current[0] for previous, current in zip(gaps, gaps[1:])):
        raise ValueError("Coverage gaps overlap")
    if len({row["id"] for row in counter_events}) != len(counter_events):
        raise ValueError("Duplicate counter event ID")
    result = []
    for event in counter_events:
        first, last = event["evidence_interval_s"]
        update = event["crossing_time_s"]
        if not first <= last <= update:
            raise ValueError("Counter evidence interval must end by update time")
        classification = "outside_route_gaps"
        selected_gap = None
        for start, end in gaps:
            update_inside = start <= update < end
            evidence_overlaps = max(start, first) < min(end, last)
            if not (update_inside or evidence_overlaps):
                continue
            selected_gap = [start, end]
            classification = (
                "counter_evidence_inside_gap"
                if start <= first and update < end
                else "boundary_ambiguous_counter_evidence"
            )
            break
        result.append({
            "counter_id": event["id"],
            "colour": event["colour"],
            "counter_update_s": update,
            "counter_evidence_interval_s": [first, last],
            "remaining_before": event["remaining_before"],
            "remaining_after": event["remaining_after"],
            "classification": classification,
            "gap_interval_s": selected_gap,
        })
    return result
