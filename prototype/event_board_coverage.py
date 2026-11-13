"""Audit whether source-matched partial boards survive an event-ledger revision."""


def audit_board_event_coverage(board_windows, legacy_events, grounded_events):
    """Join by the same delayed counter; preserve absent and conflicting events."""
    legacy_by_anchor = {}
    for event in legacy_events:
        counter = event.get("broadcast_counter")
        if counter is not None:
            legacy_by_anchor.setdefault(counter["update_s"], []).append(event)
    grounded_by_counter = {}
    for event in grounded_events:
        if event["counter_id"] is not None:
            grounded_by_counter.setdefault(event["counter_id"], []).append(event)

    output = []
    seen_windows = set()
    for board in board_windows:
        key = (board["source_video_sha256"], board["board_window_id"])
        if key in seen_windows:
            raise ValueError(f"Duplicate board window: {key}")
        seen_windows.add(key)
        matches = legacy_by_anchor.get(board["counter_anchor_s"], [])
        if len(matches) != 1:
            raise ValueError(f"Expected one legacy counter match for {key}; got {len(matches)}")
        old = matches[0]
        newer = grounded_by_counter.get(old["counter_id"], [])
        if len(newer) > 1:
            raise ValueError(f"Ambiguous grounded counter: {old['counter_id']}")
        new = newer[0] if newer else None
        if new is not None and new["colour"] != old["colour"]:
            raise ValueError(f"Grounded event changed resolved colour: {old['counter_id']}")
        output.append(
            {
                **board,
                "legacy_event": {
                    "candidate_id": old["candidate_id"],
                    "shot_id": old["shot_id"],
                    "counter_id": old["counter_id"],
                    "colour": old["colour"],
                    "colour_status": old["colour_status"],
                    "release_window_s": old["release_window_s"],
                },
                "grounded_event": (
                    {
                        "shot_id": new["shot_id"],
                        "counter_id": new["counter_id"],
                        "colour": new["colour"],
                        "colour_basis": new["colour_provenance"]["basis"],
                        "camera_continuity_status": new["camera_boundary_evidence"][
                            "continuity_status"
                        ],
                    }
                    if new is not None
                    else None
                ),
                "grounded_event_coverage": "present" if new is not None else "absent",
                "physical_transition_verified": False,
                "simulation_ready": False,
            }
        )
    return output
