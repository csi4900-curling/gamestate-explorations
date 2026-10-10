"""Keep uncertainty visible when event candidates are passed toward game state."""


def ground_event_candidates(events, possible_edit_rows, temporal_rows):
    """Add source-scoped camera and simulation limits without changing events."""
    event_ids = [row["shot_id"] for row in events]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("Duplicate event shot ID")
    temporal = {(row["shot_id"], row["time_s"]): row for row in temporal_rows}
    if len(temporal) != len(temporal_rows):
        raise ValueError("Duplicate temporal edit row")
    edit_keys = [(row["shot_id"], row["time_s"]) for row in possible_edit_rows]
    if len(edit_keys) != len(set(edit_keys)) or set(edit_keys) != set(temporal):
        raise ValueError("Possible-edit and temporal rows differ")
    edits_by_shot = {}
    for row in possible_edit_rows:
        edits_by_shot.setdefault(row["shot_id"], []).append(row)
    output = []
    for event in events:
        shot_id = event["shot_id"]
        window = event["delivery_window_s"]
        edits = []
        for row in sorted(edits_by_shot.get(shot_id, []),
                          key=lambda item: item["time_s"]):
            time_s = row["time_s"]
            if not window[0] < time_s < window[1]:
                raise ValueError(f"Internal edit lies outside event window: {shot_id}")
            crossing_ids = row["crossing_same_shot_cap_track_ids"]
            if len(crossing_ids) != row["crossing_same_shot_cap_track_count"]:
                raise ValueError(f"Crossing track count mismatch: {shot_id}")
            edits.append({
                "time_s": time_s,
                "evidence_tier": "isolated_spike" if temporal[(shot_id, time_s)][
                    "isolated_spike"] else "nonisolated_change",
                "crossing_same_shot_cap_track_ids": list(crossing_ids),
                "boundary_status": "possible_unverified",
            })
        crossing = any(row["crossing_same_shot_cap_track_ids"] for row in edits)
        if crossing:
            continuity = "possible_edit_crosses_cap_track"
        elif edits:
            continuity = "possible_edit_without_crossing_cap_track"
        else:
            continuity = "no_proposed_internal_edit"
        enriched = dict(event)
        enriched["camera_boundary_evidence"] = {
            "possible_internal_edits": edits,
            "continuity_status": continuity,
            "physical_stone_identity_verified": False,
        }
        enriched["simulation_handoff"] = {
            "simulation_ready": False,
            "exact_release_time_s": None,
            "delivered_stone_identity": None,
            "continuous_physical_trajectory": None,
            "settled_board_transition": None,
        }
        output.append(enriched)
    return output
