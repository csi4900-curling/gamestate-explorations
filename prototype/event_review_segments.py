"""Turn provisional event evidence into source-video review clips."""


def build_review_segments(events, shots, possible_edits, *, before_s=2.0,
                          after_s=5.0):
    """Return review intervals; never claim physical release or settling times."""
    shot_by_id = {shot["id"]: shot for shot in shots}
    if len(shot_by_id) != len(shots):
        raise ValueError("Duplicate camera shot ID")
    shot_index = {shot["id"]: i for i, shot in enumerate(shots)}
    assigned = {}
    for event in events:
        for shot_id in event["source_shot_ids"]:
            if shot_id not in shot_by_id:
                raise ValueError(f"Unknown event camera shot: {shot_id}")
            if shot_id in assigned:
                raise ValueError(f"Camera shot assigned to multiple events: {shot_id}")
            assigned[shot_id] = event["event_id"]
    source_start, source_end = shots[0]["interval_s"][0], shots[-1]["interval_s"][1]
    rows = []
    for event in events:
        source_ids = list(event["source_shot_ids"])
        included_previous = None
        if (event["candidate_class"] == "counter_linked_travel_only_provisional"
                and event["attached_held_evidence"] is None):
            first_id = min(source_ids, key=lambda shot_id: shot_index[shot_id])
            first_index = shot_index[first_id]
            if first_index:
                previous = shots[first_index - 1]["id"]
                if previous not in assigned:
                    source_ids.insert(0, previous)
                    included_previous = previous
        intervals = [shot_by_id[shot_id]["interval_s"] for shot_id in source_ids]
        core = [min(interval[0] for interval in intervals),
                max(interval[1] for interval in intervals)]
        review = [max(source_start, round(core[0] - before_s, 3)),
                  min(source_end, round(core[1] + after_s, 3))]
        edits = [round(row["time_s"], 3) for row in possible_edits
                 if core[0] < row["time_s"] < core[1]]
        rows.append({
            "event_id": event["event_id"],
            "candidate_class": event["candidate_class"],
            "counter_id": event["counter_id"],
            "colour": event["colour"],
            "colour_status": event["colour_status"],
            "evidence_shot_ids": event["source_shot_ids"],
            "review_shot_ids": source_ids,
            "unoccupied_previous_shot_added": included_previous,
            "evidence_core_s": core,
            "review_window_s": review,
            "possible_internal_edit_times_s": edits,
            "delivery_window_s": event["delivery_window_s"],
            "observed_travel_window_s": event["observed_travel_window_s"],
            "physical_release_time_s": None,
            "physical_settle_time_s": None,
            "physical_stone_identity_verified": False,
            "simulation_ready": False,
        })
    rows.sort(key=lambda row: (row["evidence_core_s"][0], row["event_id"]))
    return rows
