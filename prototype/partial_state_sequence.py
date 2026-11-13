"""Conservative event-to-board sequence built from video evidence only."""


def build_partial_state_sequence(screen, boards, comparisons, source_reviews=()):
    """Join accepted passage events to observed boards and adjacent comparisons.

    A row is an observation after a candidate, never a complete physical state.
    Unmatched stone proposals never imply births, removals or collisions.
    """
    if not (screen["source_sha256"] == boards["source_sha256"] == comparisons["source_sha256"]):
        raise ValueError("Source fingerprints differ")
    events = sorted(screen["events"], key=lambda row: row["crossing_time_s"])
    event_ids = [row["id"] for row in events]
    if len(set(event_ids)) != len(event_ids):
        raise ValueError("Duplicate accepted event ID")
    decisions = screen["decisions"]
    if len({row["candidate_id"] for row in decisions}) != len(decisions):
        raise ValueError("Duplicate screen decision ID")
    accepted = {row["candidate_id"] for row in decisions if row["accepted"]}
    if accepted != set(event_ids):
        raise ValueError("Screen decisions and accepted events differ")
    board_by_id = {row["candidate_id"]: row for row in boards["rows"]}
    if len(board_by_id) != len(boards["rows"]) or set(board_by_id) != accepted:
        raise ValueError("Board coverage differs from accepted events")
    comparison_by_after = {row["after_candidate_id"]: row for row in comparisons["comparisons"]}
    if len(comparison_by_after) != len(comparisons["comparisons"]):
        raise ValueError("Duplicate adjacent comparison")
    if set(comparison_by_after) != set(event_ids[1:]):
        raise ValueError("Comparison coverage differs from adjacent events")
    reviews = {}
    for review in source_reviews:
        event_id = review["candidate_id"]
        if (
            event_id in reviews
            or event_id not in accepted
            or review["source_sha256"] != screen["source_sha256"]
            or review["status"] != "agent_source_review_not_independent_validation"
        ):
            raise ValueError(f"Invalid or duplicate source review: {event_id}")
        reviews[event_id] = review
    rows = []
    for index, event in enumerate(events):
        event_id = event["id"]
        board = board_by_id[event_id]
        if (
            board["crossing_time_s"] != event["crossing_time_s"]
            or board["colour"] != event["colour"]
        ):
            raise ValueError(f"Event and board anchors differ: {event_id}")
        stones = board["board"]["stones"]
        local_ids = [stone["local_observation_id"] for stone in stones]
        if len(set(local_ids)) != len(local_ids):
            raise ValueError(f"Duplicate local stone observation: {event_id}")
        before_id = event_ids[index - 1] if index else None
        comparison = comparison_by_after.get(event_id)
        if comparison and (
            comparison["before_candidate_id"] != before_id
            or comparison["after_candidate_id"] != event_id
        ):
            raise ValueError(f"Nonadjacent comparison: {event_id}")
        if comparison and comparison["status"] == "view_local_partial_comparison":
            prev_stones = board_by_id[before_id]["board"]["stones"]
            prev_ids = {stone["local_observation_id"] for stone in prev_stones}
            for pair in comparison["matched_observations"]:
                if (
                    pair["before_local_observation_id"] not in prev_ids
                    or pair["after_local_observation_id"] not in local_ids
                ):
                    raise ValueError(f"Comparison cites unknown observation: {event_id}")
        blockers = [
            "physical_throw_identity_unverified",
            "complete_board_unverified",
            "metric_geometry_unvalidated",
            "persistent_stone_identity_unverified",
            "release_and_settle_times_unverified",
        ]
        if not stones:
            blockers.append("no_stable_post_event_board")
        if comparison and comparison["status"] != "view_local_partial_comparison":
            blockers.append("adjacent_state_transition_unobserved")
        if comparison and not comparison["same_end_verified"]:
            blockers.append("same_end_unverified")
        review = reviews.get(event_id)
        if review and review["review_conclusion"].startswith("false_positive_"):
            blockers.append("source_reviewed_false_path")
        rows.append(
            {
                "candidate_id": event_id,
                "candidate_colour": event["colour"],
                "passage_time_s": event["crossing_time_s"],
                "passage_time_semantics": event["time_semantics"],
                "physical_throw_identity_verified": False,
                "agent_source_review": {
                    "status": review["status"],
                    "conclusion": review["review_conclusion"],
                    "basis": review["basis"],
                    "independent_validation": False,
                }
                if review
                else None,
                "post_event_observation": {
                    "status": board["board"]["status"],
                    "receiving_view": board["receiving_view"],
                    "quiet_tail_s": [board["tail"]["start_s"], board["tail"]["stop_s"]]
                    if board["tail"]["eligible"]
                    else None,
                    "coordinate_frame": board["coordinate_frame"],
                    "stones": [
                        {
                            "local_observation_id": stone["local_observation_id"],
                            "colour": stone["colour"],
                            "position_m_conditional": stone["view_local_ground_position_m"],
                            "first_seen_s": stone["first_seen_s"],
                            "last_seen_s": stone["last_seen_s"],
                            "supporting_frame_count": stone["supporting_frame_count"],
                            "max_position_spread_m": stone["max_position_spread_m"],
                            "persistent_stone_identity": None,
                        }
                        for stone in stones
                    ],
                    "completeness": board["completeness"],
                    "physical_settle_verified": board["post_throw_settle_verified"],
                },
                "transition_from_previous_candidate": {
                    "before_candidate_id": before_id,
                    "status": comparison["status"] if comparison else "no_previous_candidate",
                    "matched_local_observations": comparison.get("matched_observations", [])
                    if comparison
                    else [],
                    "unmatched_before_local_ids": comparison.get("before_only_observations", [])
                    if comparison
                    else [],
                    "unmatched_after_local_ids": comparison.get("after_only_observations", [])
                    if comparison
                    else [],
                    "intervening_passage_candidate_ids": comparison.get(
                        "intervening_passage_candidate_ids", []
                    )
                    if comparison
                    else [],
                    "same_end_verified": comparison["same_end_verified"] if comparison else False,
                    "physical_additions_removals_or_collisions_inferred": False,
                },
                "simulation_ready": False,
                "simulation_blockers": blockers,
            }
        )
    return {
        "status": "provisional_event_partial_state_sequence_not_simulation_ready",
        "source_id": screen["source_id"],
        "source_sha256": screen["source_sha256"],
        "source_interval_s": screen["source_interval_s"],
        "event_count": len(rows),
        "agent_source_review_count": len(reviews),
        "agent_source_reviewed_false_path_ids": sorted(
            event_id
            for event_id, review in reviews.items()
            if review["review_conclusion"].startswith("false_positive_")
        ),
        "withheld_screen_candidate_ids": sorted(
            row["candidate_id"] for row in decisions if not row["accepted"]
        ),
        "observed_board_count": sum(bool(row["post_event_observation"]["stones"]) for row in rows),
        "comparable_transition_count": sum(
            row["transition_from_previous_candidate"]["status"] == "view_local_partial_comparison"
            for row in rows
        ),
        "simulation_ready_count": 0,
        "events": rows,
    }
