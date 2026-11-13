"""Add source-only two-view release proposals to a provisional event union."""


def append_source_release_rescues(events, proposals, receiving_rows):
    """Create provisional events only for unused source shots and timed cues."""
    rows = [dict(row) for row in events]
    used_shots = {shot for event in events for shot in event["source_shot_ids"]}
    used_ids = {event["event_id"] for event in events}
    if len(used_ids) != len(events):
        raise ValueError("Duplicate baseline event ID")
    receivers = {row["proposal_id"]: row for row in receiving_rows}
    if len(receivers) != len(receiving_rows):
        raise ValueError("Duplicate receiving-view proposal ID")
    if set(receivers) != {row["proposal_id"] for row in proposals}:
        raise ValueError("Proposal and receiving-view rows differ")
    for proposal in proposals:
        receiving = receivers[proposal["proposal_id"]]
        origin = proposal["origin_shot_id"]
        if (
            proposal["candidate_class"] != "source_only_held_release_provisional"
            or receiving["origin_shot_id"] != origin
            or receiving["origin_colour"] != proposal["observed_colour"]
            or receiving["release_cue_s"] != proposal["release_cue_s"]
            or not receiving["hard_cut_verified"]
            or receiving["decision"]
            != {"colour": proposal["observed_colour"], "status": "unique_strict_postcut_motion"}
            or receiving["physical_stone_identity_verified"]
        ):
            raise ValueError("Source-only rescue lacks matching two-view evidence")
        tracks = receiving["tracks"][proposal["observed_colour"]]["strict"]
        if len(tracks) != 1:
            raise ValueError("Receiving motion is not a unique strict track")
        start, end = proposal["origin_shot_interval_s"]
        cut = receiving["cut_time_s"]
        receiver_end = receiving["receiving_window_s"][1]
        if (
            end != cut
            or not start < proposal["release_cue_s"] < cut
            or not cut <= tracks[0]["time_interval_s"][0] < receiver_end
        ):
            raise ValueError("Release, cut and receiving track are not ordered")
        receiver_shot = receiving["receiving_shot_id"]
        if origin == receiver_shot or {origin, receiver_shot} & used_shots:
            raise ValueError("Rescue reuses an assigned camera shot")
        if any(
            event["delivery_window_s"][0] < end and event["delivery_window_s"][1] > start
            for event in rows
        ):
            raise ValueError("Rescue overlaps an existing event delivery window")
        if any(
            event["observed_travel_window_s"]
            and event["observed_travel_window_s"][0] < receiver_end
            and event["observed_travel_window_s"][1] > cut
            for event in rows
        ):
            raise ValueError("Rescue overlaps an existing travel interval")
        event_id = f"SOURCE-{origin}"
        if event_id in used_ids:
            raise ValueError("Duplicate rescue event ID")
        used_shots.update((origin, receiver_shot))
        used_ids.add(event_id)
        rows.append(
            {
                "event_id": event_id,
                "candidate_class": "source_only_two_view_release_provisional",
                "source_shot_ids": [origin, receiver_shot],
                "delivery_window_s": proposal["origin_shot_interval_s"],
                "observed_travel_window_s": None,
                "counter_id": None,
                "colour": proposal["observed_colour"],
                "colour_status": "two_view_source_colour_agrees_identity_unverified",
                "evidence_sources": [
                    "origin_view_held_cap_motion_over_ice",
                    "verified_camera_cut",
                    "receiving_view_strict_cap_motion",
                ],
                "attached_travel_evidence": None,
                "attached_held_evidence": {
                    "shot_id": origin,
                    "held_interval_s": proposal["held_interval_s"],
                    "release_cue_s": proposal["release_cue_s"],
                    "below_ice_fraction": proposal["below_ice_fraction"],
                },
                "attached_receiving_evidence": {
                    "shot_id": receiver_shot,
                    "motion_interval_s": tracks[0]["time_interval_s"],
                    "track_span_px": tracks[0]["span_px"],
                    "camera_motion_status": tracks[0]["camera_motion_status"],
                },
                "physical_stone_identity_verified": False,
                "settled_board_transition_verified": False,
                "simulation_ready": False,
            }
        )
    return rows
