"""Build event review contexts that never span unsupported video coverage."""

from event_review_windows import build_review_windows


def build_timeline_review_windows(timeline, *, before_s=20.0, after_s=45.0):
    runs = timeline["supported_runs"]
    observed = timeline["observed_events"]
    run_ids = [run["id"] for run in runs]
    if len(run_ids) != len(set(run_ids)):
        raise ValueError("Duplicate run ID")
    assigned = {run_id: [] for run_id in run_ids}
    for event in observed:
        run_id = event["source_run_id"]
        if run_id not in assigned:
            raise ValueError("Event refers to an unknown run")
        assigned[run_id].append(event)
    windows = []
    for run in runs:
        run_id = run["id"]
        run_events = assigned[run_id]
        payload = build_review_windows(
            run_events,
            run["interval_s"],
            before_s=before_s,
            after_s=after_s,
        )
        by_id = {event["id"]: event for event in run_events}
        for window in payload["review_windows"]:
            event = by_id[window["event_id"]]
            windows.append(
                {
                    **window,
                    "source_run_id": run_id,
                    "event_timestamp_s": event["crossing_time_s"],
                    "boundary_review_required": event["boundary_review_required"],
                    "context_clipped_at_run_start": window["review_start_s"]
                    == run["interval_s"][0],
                    "context_clipped_at_run_end": window["review_end_s"] == run["interval_s"][1],
                }
            )
    windows.sort(key=lambda row: (row["event_timestamp_s"], row["event_id"]))
    return {
        "status": "partial_coverage_review_windows",
        "source_id": timeline["source_id"],
        "source_sha256": timeline["source_sha256"],
        "source_interval_s": timeline["source_interval_s"],
        "coverage_gaps_s": timeline["coverage_gaps_s"],
        "review_windows": windows,
        "review_window_count": len(windows),
        "context_s": {"before": before_s, "after": after_s},
        "limitations": [
            "Review windows are event contexts, not physical throw boundaries.",
            "Context is clipped to sampled-layout runs; unobserved gaps remain unknown.",
            "A boundary warning reflects detector reset and source coverage uncertainty.",
            "No board completeness, stone identity, trajectory, or simulation state is inferred.",
        ],
    }
