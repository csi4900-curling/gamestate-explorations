"""Assemble routed throw observations without hiding unsupported video spans."""


def assemble_timeline(preflight, completed_runs, *, boundary_review_s=40):
    """Merge adapter artifacts for supported runs into an explicitly partial timeline.

    Each completed item is ``(preflight_run, adapter_result, artifact_path)``.
    No event is synthesized in an unknown span. The returned observed events are
    deliberately not named ``events`` so the benchmark scorer cannot mistake
    this partial timeline for exhaustive predictions over the whole recording.
    """
    if boundary_review_s < 0:
        raise ValueError("Boundary review span must be nonnegative")
    expected = [run for run in preflight["runs"] if run["layout"] != "unknown"]
    if len(completed_runs) != len(expected):
        raise ValueError("Every supported run needs one completed adapter artifact")
    observed = []
    runs = []
    for index, ((run, result, path), expected_run) in enumerate(zip(completed_runs, expected), 1):
        if run != expected_run:
            raise ValueError("Completed run differs from preflight coverage")
        if result["source_sha256"] != preflight["source_sha256"]:
            raise ValueError("Adapter source fingerprint differs from preflight")
        if result["source_id"] != preflight["source_id"]:
            raise ValueError("Adapter source ID differs from preflight")
        if result["source_interval_s"] != run["interval_s"]:
            raise ValueError("Adapter interval differs from preflight run")
        run_id = f"R{index:02}"
        seen = set()
        for event in result["events"]:
            source_event_id = event["id"]
            if source_event_id in seen:
                raise ValueError("Duplicate adapter event ID within run")
            seen.add(source_event_id)
            time_s = event["crossing_time_s"]
            if not run["interval_s"][0] <= time_s < run["interval_s"][1]:
                raise ValueError("Adapter event falls outside routed interval")
            observed.append(
                {
                    **event,
                    "id": f"{run_id}-{source_event_id}",
                    "source_event_id": source_event_id,
                    "source_run_id": run_id,
                    "seconds_from_run_boundary": round(
                        min(time_s - run["interval_s"][0], run["interval_s"][1] - time_s),
                        3,
                    ),
                    "boundary_review_required": (
                        time_s - run["interval_s"][0] < boundary_review_s
                        or run["interval_s"][1] - time_s < boundary_review_s
                    ),
                }
            )
        runs.append(
            {
                "id": run_id,
                "layout": run["layout"],
                "interval_s": run["interval_s"],
                "adapter_artifact": str(path),
                "observed_event_count": len(result["events"]),
                "boundary_status": "uncertain_at_both_ends",
            }
        )
    observed.sort(key=lambda event: (event["crossing_time_s"], event["id"]))
    return {
        "status": "partial_coverage" if preflight["coverage_gaps_s"] else "sampled_layout_coverage",
        "source_id": preflight["source_id"],
        "source_sha256": preflight["source_sha256"],
        "source_interval_s": preflight["source_interval_s"],
        "supported_runs": runs,
        "coverage_gaps_s": preflight["coverage_gaps_s"],
        "observed_events": observed,
        "observed_event_count": len(observed),
        "boundary_review_s": boundary_review_s,
        "limitations": [
            "No event recall claim is possible in unknown coverage gaps.",
            "Adapter state resets at each run boundary; nearby throws need separate review.",
            "Sampled layout support does not prove every frame in a run has that layout.",
            "Observed passages and counter changes are not exact release times or physical throw segments.",
        ],
    }
