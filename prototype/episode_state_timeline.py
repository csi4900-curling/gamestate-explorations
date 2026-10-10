"""Join full-path and partial-prefix events into one uncertainty-preserving timeline."""

from collections import Counter


def build_episode_state_timeline(base, union, partial_boards, comparisons):
    candidates = base["timeline"]
    by_candidate = {row["candidate_id"]: row for row in candidates}
    if len(by_candidate) != len(candidates):
        raise ValueError("Duplicate source candidate ID")
    union_rows = union["candidate_rows"]
    if {row["candidate_id"] for row in union_rows} != set(by_candidate) or len(union_rows) != len(
        candidates
    ):
        raise ValueError("Partial union does not cover original candidate ledger")
    group_by_candidate = {row["candidate_id"]: row["partial_episode_id"] for row in union_rows}
    board_by_episode = {row["episode_id"]: row for row in partial_boards["rows"]}
    if len(board_by_episode) != len(partial_boards["rows"]):
        raise ValueError("Duplicate partial board episode ID")
    compare_by_episode = {}
    for row in comparisons["comparisons"]:
        key = (row["episode_id"], row["direction"])
        if key in compare_by_episode:
            raise ValueError("Duplicate partial board comparison")
        compare_by_episode[key] = row
    episode_ids = {row["episode_id"] for row in union["episodes"]}
    if (
        len(episode_ids) != len(union["episodes"])
        or set(board_by_episode) != episode_ids
        or {pid for pid, _ in compare_by_episode} != episode_ids
    ):
        raise ValueError("Partial episode coverage differs")
    event_timeline = []
    for row in candidates:
        if row["event_status"] != "provisional_event":
            continue
        if group_by_candidate[row["candidate_id"]] is not None:
            raise ValueError("Frozen accepted event also belongs to partial episode")
        event_timeline.append(
            {
                "event_id": row["candidate_id"],
                "evidence_tier": "frozen_unique_path_and_patch_provisional",
                "source_candidate_ids": [row["candidate_id"]],
                "passage_time_s": row["passage_time_s"],
                "passage_time_semantics": row["passage_time_semantics"],
                "colour": row["candidate_colour"],
                "receiving_view": row["receiving_view"],
                "observed_receiving_motion": row["observed_receiving_motion"],
                "post_event_partial_board": row["post_event_partial_board"],
                "comparison_from_previous_accepted_event": row[
                    "comparison_from_previous_accepted_event"
                ],
                "physical_throw_identity_verified": False,
                "release_time_s": None,
                "physical_settle_time_s": None,
                "spin_revolution_count": None,
                "end_identity": None,
                "complete_game_state": False,
                "simulation_ready": False,
            }
        )
    for episode in union["episodes"]:
        eid = episode["episode_id"]
        root = by_candidate[episode["root_candidate_id"]]
        members = episode["candidate_ids"]
        if any(
            by_candidate[pid]["event_status"] != "screen_abstention"
            or group_by_candidate[pid] != eid
            for pid in members
        ):
            raise ValueError("Partial episode includes non-abstained candidate")
        board = board_by_episode[eid]
        if (
            board["candidate_ids"] != members
            or board["receiving_view"] != episode["receiving_view"]
        ):
            raise ValueError("Partial episode board differs from motion")
        before = compare_by_episode.get((eid, "from_previous_accepted"))
        after = compare_by_episode.get((eid, "to_next_accepted"))
        if before is None or after is None:
            raise ValueError("Missing neighboring board comparison")
        event_timeline.append(
            {
                "event_id": eid,
                "evidence_tier": "postscore_shared_prefix_partial_review_proposal",
                "source_candidate_ids": members,
                "passage_time_s": min(episode["candidate_passage_times_s"].values()),
                "passage_time_semantics": root["passage_time_semantics"],
                "candidate_passage_times_s": episode["candidate_passage_times_s"],
                "colour": episode["colour"],
                "receiving_view": episode["receiving_view"],
                "observed_interval_s": episode["observed_interval_s"],
                "first_ambiguity_time_s": episode["first_ambiguity_time_s"],
                "cross_view_overlap_identity_verified": False,
                "overlapping_passages": episode["overlapping_passages"],
                "observed_receiving_motion": episode["observed_receiving_motion"],
                "post_event_partial_board": {
                    "status": board["board"]["status"],
                    "tail_interval_s": [board["tail"]["start_s"], board["tail"]["stop_s"]]
                    if board["tail"]["eligible"]
                    else None,
                    "registered_frame_count": board["registered_frame_count"],
                    "registration_abstention_count": board["registration_abstention_count"],
                    "coordinate_frame": board["coordinate_frame"],
                    "stones": board["board"]["stones"],
                    "completeness": board["completeness"],
                    "settle_verified": board["post_throw_settle_verified"],
                },
                "comparison_from_previous_accepted_event": before,
                "comparison_to_next_accepted_event": after,
                "physical_throw_identity_verified": False,
                "release_time_s": None,
                "physical_settle_time_s": None,
                "spin_revolution_count": None,
                "end_identity": None,
                "complete_game_state": False,
                "simulation_ready": False,
            }
        )
    event_timeline.sort(key=lambda row: (row["passage_time_s"], row["event_id"]))
    ids = [row["event_id"] for row in event_timeline]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate event-level proposal ID")
    candidate_timeline = [
        {**row, "partial_episode_id": group_by_candidate[row["candidate_id"]]} for row in candidates
    ]
    return {
        "candidate_timeline": candidate_timeline,
        "event_timeline": event_timeline,
        "event_proposal_status_counts": dict(
            Counter(row["evidence_tier"] for row in event_timeline)
        ),
    }
