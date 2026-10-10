"""Order candidate throws while preserving uncertain timing and counter state."""


def build_throw_event_ledger(origin_events, travel_rows, counter_events):
    """Return chronological candidates with observed counter transitions.

    Counter remaining-stone counts are broadcast observations, not a complete
    game state. A visual-only candidate has no implied counter transition.
    """
    by_counter = {row["id"]: row for row in counter_events}
    if len(by_counter) != len(counter_events):
        raise ValueError("Duplicate counter event ID")
    candidates = []
    for event in origin_events:
        start, end = event["delivery_window_s"]
        candidates.append({"evidence_class": "origin_view_candidate",
                           "shot_id": event["shot_id"],
                           "release_window_s": [start, end],
                           "observed_travel_window_s": None,
                           "observation_anchor_s": start,
                           "colour": event["colour"],
                           "colour_status": event["colour_status"],
                           "evidence_sources": event["evidence_sources"],
                           "counter_id": event["counter_id"]})
    for row in travel_rows:
        if row["status"] != "unlocalized_travel_candidate":
            continue
        candidates.append({"evidence_class": "travel_only_counter_candidate",
                           "shot_id": row["travel_shot_id"],
                           "release_window_s": row["release_window_s"],
                           "observed_travel_window_s": row["observed_travel_window_s"],
                           "observation_anchor_s": row["observed_travel_window_s"][0],
                           "colour": row["colour"], "colour_status": "counter_observed",
                           "evidence_sources": ["counter_and_dual_channel_travel_motion"],
                           "counter_id": row["counter_id"]})
    used_shots = set()
    used_counters = set()
    for candidate in candidates:
        shot_id = candidate["shot_id"]
        counter_id = candidate["counter_id"]
        if shot_id in used_shots or (counter_id and counter_id in used_counters):
            raise ValueError("Duplicate shot or counter assigned to candidate events")
        used_shots.add(shot_id)
        if counter_id:
            if counter_id not in by_counter:
                raise ValueError(f"Unknown counter ID: {counter_id}")
            used_counters.add(counter_id)
            counter = by_counter[counter_id]
            if (candidate["release_window_s"] is not None
                    and candidate["release_window_s"][0] > counter["crossing_time_s"] + 1):
                raise ValueError(
                    f"Counter {counter_id} updates before candidate {shot_id} release window")
            candidate["broadcast_counter"] = {
                "update_s": counter["crossing_time_s"],
                "evidence_interval_s": counter["evidence_interval_s"],
                "remaining_before": counter["remaining_before"],
                "remaining_after": counter["remaining_after"],
            }
        else:
            candidate["broadcast_counter"] = None
    ordered_counters = sorted(counter_events, key=lambda row: row["crossing_time_s"])
    state_links = {}
    discontinuities = []
    for index, counter in enumerate(ordered_counters):
        if index == 0:
            state_links[counter["id"]] = {"status": "initial_observation",
                                          "previous_counter_id": None}
            continue
        previous = ordered_counters[index - 1]
        continuous = previous["remaining_after"] == counter["remaining_before"]
        state_links[counter["id"]] = {
            "status": "continuous" if continuous else "discontinuity",
            "previous_counter_id": previous["id"]}
        if not continuous:
            discontinuities.append({
                "previous_counter_id": previous["id"],
                "counter_id": counter["id"],
                "previous_remaining_after": previous["remaining_after"],
                "current_remaining_before": counter["remaining_before"]})
    for candidate in candidates:
        candidate["counter_state_link"] = (state_links[candidate["counter_id"]]
                                           if candidate["counter_id"] else None)
    candidates.sort(key=lambda row: (row["observation_anchor_s"], row["shot_id"]))
    for index, candidate in enumerate(candidates, 1):
        candidate["candidate_id"] = f"T{index:03d}"
    return {"events": candidates,
            "counter_state_discontinuities": discontinuities,
            "counter_updates_without_candidate": [row["id"] for row in counter_events
                                                  if row["id"] not in used_counters]}
