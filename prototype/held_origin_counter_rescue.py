"""Propose additional events from held-cap release evidence and delayed counters."""


def propose_held_origin_rescues(fused, held_rows, *, max_counter_lag_s=45.0):
    """One-to-one match only; retain every abstention and unmatched passage."""
    used_shots = {event["shot_id"] for event in fused["events"]}
    used_counters = {event["counter_id"] for event in fused["events"]
                     if event["counter_id"] is not None}
    counter_rows = fused["unassociated_counter_events"]
    if any(row["counter_id"] in used_counters for row in counter_rows):
        raise ValueError("Counter is both associated and unassociated")
    if len({row["counter_id"] for row in counter_rows}) != len(counter_rows):
        raise ValueError("Duplicate unassociated counter")
    if len({row["shot_id"] for row in held_rows}) != len(held_rows):
        raise ValueError("Duplicate held-origin shot")

    audit = []
    for row in held_rows:
        passages = row["accepted_passages"]
        colour = row["unique_passage_colour"]
        if not passages:
            continue
        if len(passages) != 1 or colour != passages[0]["colour"]:
            audit.append({"shot_id": row["shot_id"], "status": "ambiguous_passages",
                          "counter_options": [], "proposed_event": None})
            continue
        passage = passages[0]
        options = [counter for counter in counter_rows
                   if counter["colour"] == colour and
                   0 <= counter["counter_update_s"] - passage["release_cue_s"]
                   <= max_counter_lag_s]
        audit.append({
            "shot_id": row["shot_id"],
            "status": ("existing_fused_shot" if row["shot_id"] in used_shots else
                       "no_counter_match" if not options else
                       "ambiguous_counters" if len(options) > 1 else
                       "pending_unique_match"),
            "counter_options": [counter["counter_id"] for counter in options],
            "proposed_event": None,
            "passage": passage,
            "origin_interval_s": row["origin_interval_s"],
        })
    competing = {}
    for row in audit:
        if row["status"] == "pending_unique_match":
            competing.setdefault(row["counter_options"][0], []).append(row)
    for rows in competing.values():
        if len(rows) > 1:
            for row in rows:
                row["status"] = "competing_held_passages"
    counter_by_id = {row["counter_id"]: row for row in counter_rows}
    proposals = []
    for row in audit:
        if row["status"] != "pending_unique_match":
            continue
        counter = counter_by_id[row["counter_options"][0]]
        passage = row["passage"]
        proposal = {
            "shot_id": row["shot_id"],
            "delivery_window_s": row["origin_interval_s"],
            "held_interval_s": passage["held_interval_s"],
            "release_cue_s": passage["release_cue_s"],
            "counter_id": counter["counter_id"],
            "counter_update_s": counter["counter_update_s"],
            "colour": passage["colour"],
            "below_ice_fraction": passage["below_ice_fraction"],
            "evidence_sources": ["held_cap_motion_over_ice", "delayed_counter"],
            "status": "provisional_rescue_candidate",
            "physical_stone_identity_verified": False,
            "exact_release_time_verified": False,
            "simulation_ready": False,
        }
        row["status"] = "provisional_rescue_candidate"
        row["proposed_event"] = proposal
        proposals.append(proposal)
    return {"proposals": proposals, "passage_audit": audit}
