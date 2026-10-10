"""Add counter-linked receiving travel preceded by an unassigned origin-like view."""


def append_preorigin_travel_rescues(events, proposals):
    """Append provisional events without asserting exact release or cross-view identity."""
    rows = [dict(event) for event in events]
    used_ids = {row["event_id"] for row in rows}
    used_shots = {shot for row in rows for shot in row["source_shot_ids"]}
    used_counters = {row["counter_id"] for row in rows if row["counter_id"]}
    if len(used_ids) != len(rows) or len(used_counters) != sum(
            bool(row["counter_id"]) for row in rows):
        raise ValueError("Baseline event or counter IDs are not unique")
    for proposal in proposals:
        origin = proposal["origin_shot_id"]
        receiver = proposal["receiving_shot_id"]
        counter = proposal["counter_id"]
        track = proposal["receiving_track"]
        delivery_start, cut = proposal["origin_shot_interval_s"]
        receiver_start, receiver_end = proposal["receiving_shot_interval_s"]
        if (proposal["proposal_id"] != f"TRAVEL-{counter}" or
                proposal["visible_release_cue_s"] is not None or
                proposal["physical_stone_identity_verified"] or
                proposal["simulation_ready"] or
                origin == receiver or origin in used_shots or receiver in used_shots or
                counter in used_counters or proposal["proposal_id"] in used_ids):
            raise ValueError("Travel rescue duplicates or overstates existing evidence")
        if (not delivery_start < cut == receiver_start < receiver_end or
                not cut <= track["interval_s"][0] < track["interval_s"][1]
                <= receiver_end or
                not receiver_end <= proposal["counter_time_s"] <= receiver_end + 5 or
                track["colour"] != proposal["counter_colour"] or
                track["span_px"] < 100 or track["point_count"] < 10):
            raise ValueError("Origin, travel and counter evidence are not ordered")
        if any(row["delivery_window_s"][0] < cut and
               row["delivery_window_s"][1] > delivery_start for row in rows):
            raise ValueError("Travel rescue overlaps another delivery window")
        if any(row["observed_travel_window_s"] and
               row["observed_travel_window_s"][0] < track["interval_s"][1]
               and row["observed_travel_window_s"][1] > track["interval_s"][0]
               for row in rows):
            raise ValueError("Travel rescue overlaps another receiving track")
        rows.append({
            "event_id": proposal["proposal_id"],
            "candidate_class": "counter_linked_preorigin_travel_provisional",
            "source_shot_ids": [origin, receiver],
            "delivery_window_s": proposal["origin_shot_interval_s"],
            "observed_travel_window_s": track["interval_s"],
            "counter_id": counter,
            "colour": track["colour"],
            "colour_status": "counter_and_receiving_travel_agree_origin_colour_unverified",
            "evidence_sources": ["origin_view_model", "verified_camera_cut",
                                 "receiving_view_cap_travel", "delayed_counter"],
            "attached_travel_evidence": {
                "shot_id": receiver,
                "window_s": track["interval_s"],
                "channel_support": [{"channel": "cap", "tracks": [track]}],
                "counter_time_s": proposal["counter_time_s"],
            },
            "attached_held_evidence": None,
            "visible_release_cue_s": None,
            "physical_stone_identity_verified": False,
            "settled_board_transition_verified": False,
            "simulation_ready": False,
        })
        used_ids.add(proposal["proposal_id"])
        used_shots.update((origin, receiver))
        used_counters.add(counter)
    return rows
