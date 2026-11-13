"""Build one source-scoped event evidence ledger without forced identity merges."""


def combine_event_evidence(linked_events, travel_rows, relation_rows, held_proposals):
    """Attach corroboration by counter and add only unoccupied travel/held cues."""
    relations = {row["counter_id"]: row for row in relation_rows}
    if len(relations) != len(relation_rows):
        raise ValueError("Duplicate travel relation counter")
    travel = {
        row["counter_id"]: row
        for row in travel_rows
        if row["status"] == "unlocalized_travel_candidate"
    }
    if len(travel) != sum(row["status"] == "unlocalized_travel_candidate" for row in travel_rows):
        raise ValueError("Duplicate travel counter")
    if set(travel) != set(relations):
        raise ValueError("Travel proposals and relation rows differ")
    held = {row["counter_id"]: row for row in held_proposals}
    if len(held) != len(held_proposals):
        raise ValueError("Duplicate held counter")

    events = []
    by_counter = {}
    occupied_shots = set()
    for source in linked_events:
        shot = source["shot_id"]
        if shot in occupied_shots:
            raise ValueError(f"Duplicate baseline shot: {shot}")
        occupied_shots.add(shot)
        counter = source["counter_id"]
        if counter is not None and counter in by_counter:
            raise ValueError(f"Duplicate linked counter: {counter}")
        row = {
            "event_id": f"VISUAL-{shot}",
            "candidate_class": "visual_origin_existing",
            "source_shot_ids": [shot],
            "delivery_window_s": source["delivery_window_s"],
            "observed_travel_window_s": None,
            "counter_id": counter,
            "colour": source["colour"],
            "colour_status": source["colour_status"],
            "evidence_sources": list(source["evidence_sources"]),
            "attached_travel_evidence": None,
            "attached_held_evidence": None,
            "physical_stone_identity_verified": False,
            "settled_board_transition_verified": False,
            "simulation_ready": False,
        }
        events.append(row)
        if counter is not None:
            by_counter[counter] = row

    unassigned = []
    for counter, cue in travel.items():
        relation = relations[counter]
        if relation["travel_shot_id"] != cue["travel_shot_id"]:
            raise ValueError(f"Travel relation shot differs: {counter}")
        evidence = {
            "shot_id": cue["travel_shot_id"],
            "window_s": cue["observed_travel_window_s"],
            "channel_support": cue["candidate_shots"][0]["channel_support"],
            "relation_to_preceding_event": relation["relation_status"],
        }
        if counter in by_counter:
            by_counter[counter]["attached_travel_evidence"] = evidence
            by_counter[counter]["source_shot_ids"].append(cue["travel_shot_id"])
            continue
        if relation["possible_same_physical_throw"]:
            unassigned.append(
                {
                    "counter_id": counter,
                    "reason": "possible_existing_visual_event",
                    "travel_shot_id": cue["travel_shot_id"],
                    "preceding_fused_event": relation["preceding_fused_event"],
                    "relation_status": relation["relation_status"],
                }
            )
            continue
        shot = cue["travel_shot_id"]
        if shot in occupied_shots:
            raise ValueError(f"Travel shot already occupied: {shot}")
        occupied_shots.add(shot)
        row = {
            "event_id": f"TRAVEL-{counter}",
            "candidate_class": "counter_linked_travel_only_provisional",
            "source_shot_ids": [shot],
            "delivery_window_s": cue["release_window_s"],
            "observed_travel_window_s": cue["observed_travel_window_s"],
            "counter_id": counter,
            "colour": cue["colour"],
            "colour_status": "counter_and_travel_agree_not_identity_verified",
            "evidence_sources": [
                "delayed_counter",
                "cap_travel_motion",
                "learned_box_travel_motion",
            ],
            "attached_travel_evidence": evidence,
            "attached_held_evidence": None,
            "physical_stone_identity_verified": False,
            "settled_board_transition_verified": False,
            "simulation_ready": False,
        }
        events.append(row)
        by_counter[counter] = row

    for counter, cue in held.items():
        evidence = {
            "shot_id": cue["shot_id"],
            "held_interval_s": cue["held_interval_s"],
            "release_cue_s": cue["release_cue_s"],
            "below_ice_fraction": cue["below_ice_fraction"],
        }
        if counter in by_counter:
            row = by_counter[counter]
            if row["colour"] is not None and row["colour"] != cue["colour"]:
                raise ValueError(f"Held cue contradicts resolved event colour: {counter}")
            row["attached_held_evidence"] = evidence
            if cue["shot_id"] not in row["source_shot_ids"]:
                row["source_shot_ids"].append(cue["shot_id"])
            continue
        if any(row["counter_id"] == counter for row in unassigned):
            raise ValueError(f"Held cue overlaps unresolved travel ambiguity: {counter}")
        shot = cue["shot_id"]
        if shot in occupied_shots:
            raise ValueError(f"Held shot already occupied: {shot}")
        occupied_shots.add(shot)
        row = {
            "event_id": f"HELD-{counter}",
            "candidate_class": "counter_linked_held_origin_provisional",
            "source_shot_ids": [shot],
            "delivery_window_s": cue["delivery_window_s"],
            "observed_travel_window_s": None,
            "counter_id": counter,
            "colour": cue["colour"],
            "colour_status": "counter_and_held_cue_agree_not_identity_verified",
            "evidence_sources": ["held_cap_motion_over_ice", "delayed_counter"],
            "attached_travel_evidence": None,
            "attached_held_evidence": evidence,
            "physical_stone_identity_verified": False,
            "settled_board_transition_verified": False,
            "simulation_ready": False,
        }
        events.append(row)
        by_counter[counter] = row

    if len({row["event_id"] for row in events}) != len(events):
        raise ValueError("Duplicate event ID")
    return {"events": events, "unassigned_travel_evidence": unassigned}
