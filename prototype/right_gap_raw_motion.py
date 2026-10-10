"""Relaxed camera-local motion evidence for left events lacking a right path."""

from right_bidirectional_span import bidirectional_spans


def latest_short_motion(track, event, *, displacement_px=30,
                        max_duration_s=5, min_first_cap_area_px2=5,
                        max_cross_view_lag_s=20):
    """Return one latest supported short raw-track tail near a left event."""
    if track["colour"] != event["colour"]:
        return None
    points = track["points"]
    t_left = event["crossing_time_s"]
    chosen = None
    for seed, point in enumerate(points):
        if abs(point["time_s"] - t_left) > max_cross_view_lag_s:
            continue
        found = bidirectional_spans([{**track, "points": points[seed:]}],
                                    displacement_px=displacement_px,
                                    max_duration_s=max_duration_s,
                                    min_first_cap_area_px2=min_first_cap_area_px2)
        if not found:
            continue
        candidate = found[0]
        if len(candidate["observed_prefix_points"]) < 3:
            continue
        t_right = candidate["passage"]["time_s"]
        direction = candidate["direction"]
        if not ((direction == "negative_y" and
                 0 <= t_right - t_left <= max_cross_view_lag_s)
                or (direction == "positive_y" and
                    0 <= t_left - t_right <= max_cross_view_lag_s)):
            continue
        chosen = {**candidate, "seed_start_index": seed,
                  "seed_kind": "latest_relaxed_short_raw_tail",
                  "left_event_id_for_targeted_search": event["id"]}
    return chosen


def rescue_left_only(left_events, raw_tracks_by_run, *, supported_runs):
    rows = []
    for event in left_events:
        t_left = event["crossing_time_s"]
        run_id = next((run_id for run_id, (start, stop) in supported_runs.items()
                       if start <= t_left < stop), None)
        if run_id is None:
            raise ValueError(f"Left event {event['id']} outside supported runs")
        candidates = []
        for track in raw_tracks_by_run[run_id]:
            candidate = latest_short_motion(track, event)
            if candidate:
                candidates.append(candidate)
        candidates.sort(key=lambda row: (abs(row["passage"]["time_s"] - t_left),
                                         row["raw_track_id"]))
        rows.append({"left_event_id": event["id"],
                     "left_colour_claim": event["colour"],
                     "left_passage_time_s": t_left,
                     "run_id": run_id,
                     "candidate_count": len(candidates),
                     "candidates": candidates,
                     "physical_cross_view_identity_verified": False})
    return rows
