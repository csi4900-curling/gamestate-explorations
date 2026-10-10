"""Conservative camera-aware fusion of right entries and left event evidence."""

from collections import Counter


def right_entries(right):
    """Accept complete-transfer and bounded static-left right-entry artifacts."""
    if "entry_review_proposals" in right:
        return [{**entry, "right_entry_id": entry.get("right_entry_id",
                 entry["raw_track_id"])} for entry in right["entry_review_proposals"]]
    return [{**entry, "right_entry_id": entry.get("right_entry_id",
             f"I{index:02}:{entry['raw_track_id']}")}
            for index, interval in enumerate(right["intervals"], 1)
            for entry in interval["entry_review_proposals"]]


def left_events(left):
    return left["events"] if "events" in left else left["observed_events"]


def coverage_at(coverage, time_s):
    """Return one conservative left-camera coverage status for a source time."""
    if "revised_supported_runs" in coverage:
        supported = coverage["revised_supported_runs"]
        unsupported = coverage["newly_unsupported_intervals"]
        if any(a <= time_s < b for a, b in
               (row["interval_s"] for row in unsupported)):
            return "left_static_right_active"
        if any(a <= time_s < b for a, b in
               (row["interval_s"] for row in supported)):
            return "left_supported"
        return "layout_unknown"
    if "supported_runs" in coverage:
        for run in coverage["supported_runs"]:
            a, b = run["interval_s"]
            if a <= time_s < b and run["layout"] == "split_2024":
                return "left_supported"
        return "layout_unknown"
    runs = coverage["route"]["runs"]
    for run in runs:
        a, b = run["interval_s"]
        if a <= time_s < b:
            return "left_supported" if run["layout"] == "split_2024" else "layout_unknown"
    return "layout_unknown"


def left_lookback_fully_supported(coverage, start_s, stop_s):
    """Require source support over the entire possible left-to-right lag."""
    if stop_s < start_s:
        raise ValueError("Invalid lookback interval")
    boundaries = {start_s, stop_s}
    if "revised_supported_runs" in coverage:
        groups = (coverage["revised_supported_runs"],
                  coverage["newly_unsupported_intervals"])
    elif "supported_runs" in coverage:
        groups = (coverage["supported_runs"],)
    else:
        groups = (coverage["route"]["runs"],)
    for group in groups:
        for row in group:
            a, b = row["interval_s"]
            if start_s < a < stop_s:
                boundaries.add(a)
            if start_s < b < stop_s:
                boundaries.add(b)
    ordered = sorted(boundaries)
    return all(coverage_at(coverage, (a + b) / 2) == "left_supported"
               for a, b in zip(ordered, ordered[1:]))


def fuse(right, left, coverage, *, partial_state=None, max_lag_s=20):
    hashes = {right["source_sha256"], left["source_sha256"],
              coverage["source_sha256"]}
    if partial_state:
        hashes.add(partial_state["source_sha256"])
    if len(hashes) != 1:
        raise ValueError("Source fingerprints differ")
    state_by_id = ({row["candidate_id"]: row for row in partial_state["events"]}
                   if partial_state else {})
    if partial_state and len(state_by_id) != len(partial_state["events"]):
        raise ValueError("Duplicate partial-state candidate ID")
    entries = right_entries(right)
    if len({row["right_entry_id"] for row in entries}) != len(entries):
        raise ValueError("Duplicate right entry ID")
    events = left_events(left)
    rows = []
    for entry in entries:
        t = entry["entry_crossing"]["time_s"]
        cover = coverage_at(coverage, t)
        prior = sorted((event for event in events
                        if event["colour"] == entry["colour_claim"] and
                        0 <= t - event["crossing_time_s"] <= max_lag_s and
                        coverage_at(coverage, event["crossing_time_s"]) ==
                        "left_supported"),
                       key=lambda event: t - event["crossing_time_s"])
        match = prior[0] if cover == "left_supported" and len(prior) == 1 else None
        if cover == "left_static_right_active":
            status = "right_only_left_static_review"
        elif cover == "layout_unknown":
            status = "right_only_layout_unknown_review"
        elif len(prior) == 0:
            status = ("unmatched_supported_left_review" if
                      left_lookback_fully_supported(
                          coverage, max(0, t - max_lag_s), t) else
                      "right_only_prior_left_coverage_gap_review")
        elif len(prior) > 1:
            status = "ambiguous_multiple_left_events_review"
        else:
            status = "cross_view_time_colour_corrob"
        board = state_by_id.get(match["id"]) if match else None
        if match and partial_state and board is None:
            raise ValueError(f"Missing partial state for {match['id']}")
        rows.append({
            "right_entry_id": entry["right_entry_id"],
            "right_raw_track_id": entry["raw_track_id"],
            "right_colour_claim": entry["colour_claim"],
            "right_entry_time_s": t,
            "right_entry_bracket_s": entry["entry_crossing"].get("bracket_s"),
            "right_observed_prefix_interval_s": entry.get("observed_prefix_interval_s"),
            "left_coverage_status": cover,
            "fusion_status": status,
            "prior_same_colour_left_ids_within_lag": [event["id"] for event in prior],
            "conditional_left_candidate_id": match["id"] if match else None,
            "right_minus_left_lag_s": round(t - match["crossing_time_s"], 3)
                                      if match else None,
            "post_event_board_status": board["post_event_observation"]["status"]
                                       if board else None,
            "simulation_ready": False,
            "physical_cross_view_identity_verified": False,
        })
    counts = Counter(row["conditional_left_candidate_id"] for row in rows
                     if row["conditional_left_candidate_id"])
    for row in rows:
        id = row["conditional_left_candidate_id"]
        if id and counts[id] > 1:
            row["fusion_status"] = "ambiguous_multiple_right_entries_review"
            row["conditional_left_candidate_id"] = None
            row["right_minus_left_lag_s"] = None
            row["post_event_board_status"] = None
    return rows
