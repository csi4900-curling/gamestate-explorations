"""Join board-blind cap paths to replay gaps without promoting identity."""


def build_continuation_handoff(gaps, continuation, late_e096, later_onsets):
    gap_rows = gaps["rows"]
    paths = continuation["rows"]
    by_id = {row["episode_id"]: row for row in paths}
    if len(by_id) != len(paths):
        raise ValueError("Duplicate cap continuation episode")
    expected = {
        r["episode_id"]
        for r in gap_rows
        if r["observed_left_motion_path"] and r["first_same_colour_local_observation_s"] is not None
    }
    if set(by_id) != expected:
        raise ValueError("Cap continuation episode coverage differs")
    later_rows = later_onsets["rows"]
    by_later = {row["episode_id"]: row for row in later_rows}
    if len(by_later) != len(later_rows) or set(by_later) != expected:
        raise ValueError("Later board-onset episode coverage differs")
    if (
        late_e096["episode_id"] != "E096"
        or not late_e096["late_horizon_reached"]
        or late_e096["abstention_reason"]
    ):
        raise ValueError("E096 late continuation changed")
    checkpoint = next(
        r
        for r in late_e096["red_board_onset_checkpoints"]
        if r["board_local_observation_id"] == "V02"
    )
    if (
        checkpoint["first_seen_s"] != 4591.0
        or not checkpoint["distances_to_board_red_centers_px_1080"]
        or min(checkpoint["distances_to_board_red_centers_px_1080"]) >= 1
    ):
        raise ValueError("E096 late board endpoint changed")
    generic_e096 = next(
        r for r in by_later["E096"]["later_onset_checkpoints"] if r["local_observation_id"] == "V02"
    )
    if generic_e096["tracked_cap_to_onset_detection_px_1080"] != min(
        checkpoint["distances_to_board_red_centers_px_1080"]
    ):
        raise ValueError("E096 development probe outputs differ")
    rows = []
    for gap in gap_rows:
        eid = gap["episode_id"]
        path = by_id.get(eid)
        later_probe = by_later.get(eid)
        summary = None
        if path:
            if (
                path["left_motion_candidate_id"] != gap["left_motion_candidate_id"]
                or path["colour_claim"] != gap["colour_claim"]
                or path["evaluation_horizon_first_board_time_s"]
                != gap["first_same_colour_local_observation_s"]
                or path["persistent_stone_identity_verified"]
                or path["simulation_ready"]
            ):
                raise ValueError(f"Cap continuation lineage differs: {eid}")
            summary = {
                "first_board_observation_horizon_s": path["evaluation_horizon_first_board_time_s"],
                "reached_first_board_observation_horizon": path[
                    "board_blind_continuation_reached_horizon"
                ],
                "abstention_reason": path["abstention_reason"],
                "terminal_to_nearest_same_colour_board_center_px_1080": path[
                    "terminal_to_nearest_same_colour_board_center_px_1080"
                ],
                "nearby_same_colour_competitor_seen": path["any_nearby_same_colour_competitor"],
                "observed_step_count": len(path["steps"]),
                "physical_identity_verified": False,
            }
        late = None
        if eid == "E096":
            board_v02 = next(
                s for s in gap["partial_board_local_stones"] if s["local_observation_id"] == "V02"
            )
            if board_v02["first_seen_s"] != checkpoint["first_seen_s"]:
                raise ValueError("E096 V02 board onset differs")
            late = {
                "status": "provisional_late_red_board_link_hypothesis",
                "local_board_observation_id": "V02",
                "first_seen_s": checkpoint["first_seen_s"],
                "board_blind_cap_path_reached_first_seen": True,
                "cap_to_board_frame_red_center_px_1080": min(
                    checkpoint["distances_to_board_red_centers_px_1080"]
                ),
                "earlier_red_board_observation_id": "V01",
                "earlier_red_observation_does_not_match_moving_cap": True,
                "physical_identity_verified": False,
            }
        rows.append(
            {
                **gap,
                "board_blind_cap_continuation": summary,
                "later_same_colour_board_onset_probe": {
                    "continuation_status": later_probe["continuation_status"],
                    "abstention_reason": later_probe["abstention_reason"],
                    "later_onset_checkpoints": later_probe["later_onset_checkpoints"],
                    "physical_identity_verified": False,
                }
                if later_probe
                else None,
                "late_board_link_hypothesis": late,
                "settled_stone_identity_verified": False,
                "simulation_ready": False,
            }
        )
    if len(rows) != len(gap_rows) or any(
        r["simulation_ready"] or r["settled_stone_identity_verified"] for r in rows
    ):
        raise ValueError("Replay gap conservation or readiness failed")
    return rows
