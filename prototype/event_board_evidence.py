"""Link provisional video events to partial video boards by source evidence.

An exact shared delayed-counter timestamp is a bookkeeping link. It does not
prove physical throw identity, a settled complete board, or stone continuity.
"""


def link_event_boards(observations, ledgers):
    """Return source-scoped links, preserving ambiguous and missing joins."""
    ledger_by_source = {row["source_sha256"]: row for row in ledgers}
    if len(ledger_by_source) != len(ledgers):
        raise ValueError("Duplicate event-ledger source")
    output = []
    for board in observations:
        source = board["source_video_sha256"]
        if source not in ledger_by_source:
            raise ValueError(f"No event ledger for board source {source}")
        if board["state_status"] != "partial_video_observation":
            raise ValueError("Expected video-derived partial board")
        if board["simulation_ready"] is not False:
            raise ValueError("Input claims unsupported simulation readiness")
        anchor = board["counter_anchor_s"]
        candidates = [
            event
            for event in ledger_by_source[source]["events"]
            if event.get("broadcast_counter") is not None
            and event["broadcast_counter"]["update_s"] == anchor
        ]
        status = (
            "unique_shared_delayed_counter"
            if len(candidates) == 1
            else "ambiguous_shared_delayed_counter"
            if candidates
            else "no_shared_delayed_counter"
        )
        event_refs = [
            {
                "candidate_id": event["candidate_id"],
                "colour": event["colour"],
                "colour_status": event["colour_status"],
                "evidence_class": event["evidence_class"],
                "release_window_s": event["release_window_s"],
                "observation_anchor_s": event["observation_anchor_s"],
                "counter_id": event["counter_id"],
            }
            for event in candidates
        ]
        output.append(
            {
                "board_observation_id": board["observation_id"],
                "source_video_sha256": source,
                "source_recording_code": board["source_recording_code"],
                "counter_anchor_s": anchor,
                "link_status": status,
                "event_candidates": event_refs,
                "board_observation_interval_s": board["observation_interval_s"],
                "board_stone_count": len(board["stones"]),
                "board_stones": board["stones"],
                "coordinate_frame": board["coordinate_frame"],
                "board_completeness": board["completeness"],
                "delivered_stone_identity": None,
                "physical_settle_time_s": None,
                "simulation_ready": False,
            }
        )
    return output
