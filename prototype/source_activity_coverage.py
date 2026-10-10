"""Overlay source-image activity gaps on a routed throw timeline."""


def _overlap(a, b):
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))


def overlay_active_static_left(timeline, audit, *, min_right_mae=5.0):
    """Report left-trigger coverage lost while the right panel remains active.

    Original candidate events remain unchanged; this is coverage accounting,
    not a new event detector or physical-throw label.
    """
    if timeline["source_sha256"] != audit["source_sha256"]:
        raise ValueError("Source fingerprints differ")
    bounds = timeline["source_interval_s"]
    measured = audit.get("source_interval_s")
    if measured is not None and (measured[0] > bounds[0] or measured[1] < bounds[1]):
        raise ValueError("Activity audit does not cover the timeline interval")
    supported = timeline["supported_runs"]
    original_gaps = timeline["coverage_gaps_s"]
    partitions = [row["interval_s"] for row in supported] + original_gaps
    ordered = sorted(partitions)
    if not ordered or ordered[0][0] != bounds[0] or ordered[-1][1] != bounds[1]:
        raise ValueError("Timeline partition does not cover requested interval")
    if any(left[1] != right[0] for left, right in zip(ordered, ordered[1:])):
        raise ValueError("Timeline partition has an overlap or gap")
    active = sorted((row for row in audit["static_left_runs"]
                     if row["median_right_mae"] >= min_right_mae),
                    key=lambda row: row["start_s"])
    if any(left["stop_s"] > right["start_s"] for left, right in zip(active, active[1:])):
        raise ValueError("Active static-left spans overlap")
    revised_runs = []
    newly_unsupported = []
    for run in supported:
        start, stop = run["interval_s"]
        if run["layout"] != "split_2024":
            revised_runs.append({"source_run_id": run["id"],
                                 "layout": run["layout"],
                                 "interval_s": [start, stop]})
            continue
        cursor = start
        for frozen in active:
            a, b = max(start, frozen["start_s"]), min(stop, frozen["stop_s"])
            if b <= a:
                continue
            if cursor < a:
                revised_runs.append({"source_run_id": run["id"],
                                     "layout": run["layout"],
                                     "interval_s": [cursor, a]})
            impacted = [event["id"] for event in timeline["observed_events"]
                        if a <= event["crossing_time_s"] < b]
            newly_unsupported.append({
                "interval_s": [a, b],
                "reason": "left_panel_static_while_right_panel_active",
                "source_run_id": run["id"],
                "median_left_mae": frozen["median_left_mae"],
                "median_right_mae": frozen["median_right_mae"],
                "existing_event_ids_inside": impacted,
            })
            cursor = b
        if cursor < stop:
            revised_runs.append({"source_run_id": run["id"],
                                 "layout": run["layout"],
                                 "interval_s": [cursor, stop]})
    old_supported = sum(b - a for a, b in (row["interval_s"] for row in supported))
    added_unknown = sum(b - a for a, b in
                        (row["interval_s"] for row in newly_unsupported))
    new_supported = sum(b - a for a, b in
                        (row["interval_s"] for row in revised_runs))
    if abs(old_supported - added_unknown - new_supported) > 1e-6:
        raise ValueError("Coverage seconds were not conserved")
    for row in newly_unsupported:
        if not any(_overlap(row["interval_s"], run["interval_s"]) > 0
                   for run in supported):
            raise ValueError("Added gap does not overlap supported run")
    return {
        "status": "development_source_activity_coverage_overlay_not_throw_truth",
        "source_id": timeline["source_id"],
        "source_sha256": timeline["source_sha256"],
        "source_interval_s": bounds,
        "original_supported_seconds": old_supported,
        "original_unknown_seconds": bounds[1] - bounds[0] - old_supported,
        "newly_unsupported_seconds": added_unknown,
        "revised_supported_seconds": new_supported,
        "revised_unknown_seconds": bounds[1] - bounds[0] - new_supported,
        "revised_supported_runs": revised_runs,
        "newly_unsupported_intervals": newly_unsupported,
        "original_coverage_gaps_s": original_gaps,
        "original_event_count_unchanged": len(timeline["observed_events"]),
        "minimum_right_panel_median_mae": min_right_mae,
    }
