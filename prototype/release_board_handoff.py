"""Join provisional release cues to video-derived partial board observations."""


def join_release_boards(board_links, union_games, release_games):
    """Preserve evidence by source and counter without asserting physical IDs."""
    unions = {row["source_sha256"]: row for row in union_games}
    releases = {row["source_sha256"]: row for row in release_games}
    if len(unions) != len(union_games) or len(releases) != len(release_games):
        raise ValueError("Duplicate source in event/release inputs")
    rows = []
    for board in board_links:
        source = board["source_video_sha256"]
        if source not in unions or source not in releases:
            raise ValueError("Missing source-scoped event/release ledger")
        union = unions[source]
        release = releases[source]
        if board["source_recording_code"] != union["official_game_code"]:
            raise ValueError("Board/event game code mismatch")
        refs = board["event_candidates"]
        counter = refs[0]["counter_id"] if len(refs) == 1 else None
        matching_events = [event for event in union["events"]
                           if counter is not None and event["counter_id"] == counter]
        event = matching_events[0] if len(matching_events) == 1 else None
        matching_release = [cue for cue in release["rows"]
                            if event is not None and cue["event_id"] == event["event_id"]]
        if len(matching_release) > 1:
            raise ValueError("Duplicate release sidecar event")
        cue = matching_release[0] if matching_release else None
        cue_s = cue["unique_release_cue_s"] if cue else None
        board_start = board["board_observation_interval_s"][0]
        rows.append({
            "board_observation_id": board["board_observation_id"],
            "source_video_sha256": source,
            "source_recording_code": board["source_recording_code"],
            "counter_id": counter,
            "provisional_event_id": event["event_id"] if event else None,
            "provisional_event_class": event["candidate_class"] if event else None,
            "event_join_status": "unique_shared_counter" if event else "ambiguous_or_missing",
            "board_observation_interval_s": board["board_observation_interval_s"],
            "board_stone_count": board["board_stone_count"],
            "within_view_release_cue_s": cue_s,
            "within_view_release_colour": cue["unique_passage_colour"] if cue else None,
            "release_cue_status": ("missing_event_sidecar" if cue is None else
                                   "no_unique_passage" if cue_s is None else
                                   "cue_precedes_board" if cue_s < board_start else
                                   "cue_not_before_board"),
            "cue_to_board_start_s": round(board_start - cue_s, 3)
            if cue_s is not None else None,
            "physical_stone_to_board_identity_verified": False,
            "physical_state_transition_verified": False,
            "simulation_ready": False,
        })
    return rows
