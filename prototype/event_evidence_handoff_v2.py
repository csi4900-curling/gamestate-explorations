"""Join candidate events, timed source cues, and partial boards without inventing identity."""


def join_event_evidence(events, releases, crossviews, rescue_proposals,
                        rescue_receiving, board_links, review_segments):
    """Return one evidence record per provisional event in a single recording."""
    def unique(rows, key, label):
        indexed = {row[key]: row for row in rows}
        if len(indexed) != len(rows):
            raise ValueError(f"Duplicate {label}")
        return indexed

    event_by_id = unique(events, "event_id", "event")
    release_by_id = unique(releases, "event_id", "release")
    crossview_by_id = unique(crossviews, "event_id", "cross-view")
    proposal_by_id = unique(rescue_proposals, "origin_shot_id", "rescue proposal")
    receiving_by_id = unique(rescue_receiving, "origin_shot_id", "rescue receiving")
    review_by_id = unique(review_segments, "event_id", "review segment")
    if set(review_by_id) != set(event_by_id):
        raise ValueError("Review and event IDs differ")
    boards_by_event = {}
    for board in board_links:
        event_id = board["provisional_event_id"]
        if event_id not in event_by_id or board["event_join_status"] != "unique_shared_counter":
            raise ValueError("Board link is not a unique event in this recording")
        boards_by_event.setdefault(event_id, []).append(board)
    rows = []
    for event in events:
        event_id = event["event_id"]
        if event["candidate_class"] == "source_only_two_view_release_provisional":
            origin = event["source_shot_ids"][0]
            proposal = proposal_by_id[origin]
            receiving = receiving_by_id[origin]
            if (event_id in release_by_id or event_id in crossview_by_id or
                    proposal["release_cue_s"] != event["attached_held_evidence"]["release_cue_s"] or
                    receiving["decision"]["status"] != "unique_strict_postcut_motion" or
                    not receiving["source_colour_agreement"] or
                    receiving["physical_stone_identity_verified"]):
                raise ValueError("Source-only rescue evidence mismatch")
            cue_time = proposal["release_cue_s"]
            cue_colour = proposal["observed_colour"]
            origin_shot = origin
            cue_status = "unique_passage"
            cue_route = "outside_union_source_only_scan"
            receiving_status = "source_colour_concordant_identity_unverified"
            receiving_colour = receiving["decision"]["colour"]
            receiving_motion = receiving["tracks"][cue_colour]["strict"][0][
                "time_interval_s"]
        else:
            if event_id not in release_by_id:
                raise ValueError(f"Baseline event has no release decision: {event_id}")
            release = release_by_id[event_id]
            cue_time = release["unique_release_cue_s"]
            cue_colour = release["unique_passage_colour"]
            origin_shot = release["origin_shot_id"]
            cue_status = release["scope_status"]
            cue_route = release["scope_route"]
            crossview = crossview_by_id.get(event_id)
            if crossview and cue_time is None:
                if crossview["source_colour"] is not None:
                    raise ValueError("Cross-view colour relies on a rejected release cue")
                crossview = None
            if crossview and (crossview["release_cue_s"] != cue_time or
                              crossview["passage_colour"] != cue_colour):
                raise ValueError("Cross-view and shot-scoped release cues disagree")
            receiving_status = crossview["status"] if crossview else "not_scanned"
            receiving_colour = crossview["postcut_colour"] if crossview else None
            receiving_motion = None
        linked_boards = boards_by_event.get(event_id, [])
        for board in linked_boards:
            if board["within_view_release_cue_s"] != cue_time:
                raise ValueError("Board and event release cue differ")
            if board["physical_stone_to_board_identity_verified"] or board[
                    "physical_state_transition_verified"]:
                raise ValueError("Board link claims unsupported physical identity")
        review = review_by_id[event_id]
        if review["candidate_class"] != event["candidate_class"] or review[
                "delivery_window_s"] != event["delivery_window_s"]:
            raise ValueError("Review segment differs from event")
        rows.append({
            "event_id": event_id,
            "candidate_class": event["candidate_class"],
            "source_shot_ids": event["source_shot_ids"],
            "counter_id": event["counter_id"],
            "event_colour": event["colour"],
            "event_colour_status": event["colour_status"],
            "delivery_window_s": event["delivery_window_s"],
            "review_window_s": review["review_window_s"],
            "release_cue": {"status": cue_status, "route": cue_route,
                            "origin_shot_id": origin_shot, "time_s": cue_time,
                            "colour": cue_colour},
            "receiving_view": {"status": receiving_status,
                               "colour": receiving_colour,
                               "motion_interval_s": receiving_motion,
                               "physical_stone_identity_verified": False},
            "partial_board_links": [{"board_observation_id": board[
                "board_observation_id"], "board_observation_interval_s": board[
                "board_observation_interval_s"], "board_stone_count": board[
                "board_stone_count"], "join_status": board["event_join_status"]}
                for board in linked_boards],
            "physical_release_time_s": None,
            "physical_settle_time_s": None,
            "persistent_stone_id": None,
            "continuous_trajectory": None,
            "settled_board_transition_verified": False,
            "simulation_ready": False,
        })
    if set(release_by_id) != {e["event_id"] for e in events
                                 if e["candidate_class"] !=
                                 "source_only_two_view_release_provisional"}:
        raise ValueError("Baseline release decisions do not cover baseline events")
    return rows
