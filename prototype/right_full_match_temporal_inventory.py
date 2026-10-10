"""Direction-aware temporal inventory of unreviewed right proposals."""

from collections import Counter


def candidate_left_ids(left_events, right, *, max_lag_s=20):
    t = right["passage"]["time_s"]
    direction = right["direction"]
    matches = [left for left in left_events
               if left["colour"] == right["colour_claim"]
               and ((direction == "negative_y" and
                     0 <= t - left["crossing_time_s"] <= max_lag_s)
                    or (direction == "positive_y" and
                        0 <= left["crossing_time_s"] - t <= max_lag_s))]
    return [left["id"] for left in sorted(
        matches, key=lambda left: abs(t - left["crossing_time_s"]))]


def inventory(left_events, run_proposals, *, max_lag_s=20):
    """Retain all right proposals and flag temporal disagreement for review."""
    if max_lag_s <= 0:
        raise ValueError("Positive lag window required")
    left_ids = [row["id"] for row in left_events]
    if len(left_ids) != len(set(left_ids)):
        raise ValueError("Duplicate left event ID")
    rows = []
    for run_entry in run_proposals:
        if len(run_entry) == 3:
            run_id, proposals, (run_start, run_stop) = run_entry
            run_left = [row for row in left_events
                        if run_start <= row["crossing_time_s"] < run_stop]
        else:
            run_id, proposals = run_entry
            run_left = left_events
        raw_ids = [row["raw_track_id"] for row in proposals]
        if len(raw_ids) != len(set(raw_ids)):
            raise ValueError(f"Duplicate right raw-track ID in {run_id}")
        for right in proposals:
            matches = candidate_left_ids(run_left, right,
                                         max_lag_s=max_lag_s)
            rows.append({
                "proposal_id": f"{run_id}:{right['raw_track_id']}",
                "run_id": run_id,
                "raw_track_id": right["raw_track_id"],
                "colour_claim": right["colour_claim"],
                "direction": right["direction"],
                "passage_time_s": right["passage"]["time_s"],
                "observed_prefix_interval_s": right[
                    "observed_prefix_interval_s"],
                "tail_extraction_status": right.get("tail_extraction_status"),
                "direction_aware_same_colour_left_ids_within_lag": matches,
                "temporal_status": ("no_left_time_colour_candidate" if not matches
                                    else "multiple_left_time_colour_candidates"
                                    if len(matches) > 1 else
                                    "one_left_time_colour_candidate"),
                "source_visible_class": None,
                "physical_cross_view_identity_verified": False,
                "simulation_ready": False,
            })
    claims = Counter(row["direction_aware_same_colour_left_ids_within_lag"][0]
                     for row in rows
                     if row["temporal_status"] == "one_left_time_colour_candidate")
    for row in rows:
        if (row["temporal_status"] == "one_left_time_colour_candidate"
                and claims[row["direction_aware_same_colour_left_ids_within_lag"][0]] > 1):
            row["temporal_status"] = "multiple_right_candidates_for_left_review"
    left_with_any = {candidate for row in rows for candidate in
                     row["direction_aware_same_colour_left_ids_within_lag"]}
    return {
        "rows": rows,
        "left_events_without_any_right_time_colour_candidate": [
            row["id"] for row in left_events if row["id"] not in left_with_any],
        "status_counts": dict(Counter(row["temporal_status"] for row in rows)),
    }
