"""Join independent official shot slots with provisional source-video evidence."""


def build_state_rows(
    scaffold,
    official_shots,
    official_boards,
    video_candidates,
    gap_proposals,
    orientation_cues,
    diagram_scores,
):
    by_shot = {row["official_shot_id"]: row for row in official_shots}
    by_board = {row["official_shot_id"]: row for row in official_boards}
    by_candidate = {row["shot_id"]: row for row in video_candidates}
    by_proposal = {row["official_shot_id"]: row["video_candidate_shot_id"] for row in gap_proposals}
    by_cue = {
        (row["candidate_id"], row["camera_shot_id"]): row
        for row in orientation_cues
        if row["proposed_delivery_side"]
    }
    by_score = {
        (row["video_candidate_shot_id"], row["post_camera_shot_id"]): row for row in diagram_scores
    }
    if len(by_shot) != len(official_shots) or len(by_board) != len(official_boards):
        raise ValueError("Duplicate official shot IDs")
    if len(by_candidate) != len(video_candidates):
        raise ValueError("Duplicate video candidate IDs")
    if len(by_proposal) != len(gap_proposals):
        raise ValueError("Duplicate gap proposals for official slot")
    rows = []
    used_gap_candidates = set()
    for slot in scaffold:
        shot_id = slot["official_shot_id"]
        shot = by_shot[shot_id]
        board = by_board[shot_id]
        candidate_id = slot["video_candidate_shot_id"]
        basis = (
            "counter_linked_candidate"
            if slot["counter_id"] and candidate_id
            else "counter_only"
            if slot["counter_id"]
            else "source_rescue_proposal"
            if candidate_id
            else "none"
        )
        if shot_id in by_proposal:
            if candidate_id is not None or slot["counter_id"] is not None:
                raise ValueError("Gap proposal collides with populated slot")
            candidate_id = by_proposal[shot_id]
            if candidate_id in used_gap_candidates:
                raise ValueError("Gap candidate reused")
            used_gap_candidates.add(candidate_id)
            basis = "unique_gap_order_colour_display_proposal"
        candidate = by_candidate.get(candidate_id)
        if basis == "counter_linked_candidate":
            if candidate is None or candidate["counter_id"] != slot["counter_id"]:
                raise ValueError("Counter-linked candidate missing from video scan")
        if basis == "unique_gap_order_colour_display_proposal":
            if candidate is None or candidate["counter_id"] is not None:
                raise ValueError("Gap proposal is not a counterless video candidate")
        groups = []
        if candidate is not None:
            for group in candidate["camera_shot_boards"]:
                stable = group["stable_image_relative_stones"]
                if not stable:
                    continue
                cue = by_cue.get((candidate_id, group["camera_shot_id"]))
                score = by_score.get((candidate_id, group["camera_shot_id"]))
                groups.append(
                    {
                        "camera_shot_id": group["camera_shot_id"],
                        "observation_interval_s": group["observation_interval_s"],
                        "stable_image_relative_stones": stable,
                        "layout_side_proxy": group["detected_delivery_side"],
                        "source_motion_approach_side_proposal": cue["proposed_delivery_side"]
                        if cue
                        else None,
                        "retrospective_official_diagram_comparison": (
                            {
                                "matched_observed_stones": score["current_comparison"][
                                    "matched_count"
                                ],
                                "observed_stones": score["current_comparison"]["video_stone_count"],
                                "official_symbols": score["current_comparison"][
                                    "official_symbol_count"
                                ],
                                "complete_diagram_symbol_match": score[
                                    "complete_diagram_symbol_match"
                                ],
                            }
                            if score
                            else None
                        ),
                    }
                )
        rows.append(
            {
                "official_shot_id": shot_id,
                "end": slot["end"],
                "shot_number": slot["shot_number"],
                "official_reference": {
                    "team": shot["team"],
                    "handle_colour": slot["official_colour"],
                    "shooter": shot["shooter"],
                    "shot_type": shot["shot_type"],
                    "turn_direction": shot["rotation"],
                    "turn_revolution_count": None,
                    "post_shot_diagram_stones": [
                        {
                            "colour": stone["colour"],
                            "house_radius_coordinates": stone["house_radius_coordinates"],
                        }
                        for stone in board["stones"]
                    ],
                    "post_shot_diagram_scope": "official PDF diagram only, not full rink state",
                    "schematic_diagram_replay_ready": True,
                },
                "video_event_evidence": {
                    "counter_id": slot["counter_id"],
                    "counter_crossing_time_s": slot["counter_crossing_time_s"],
                    "candidate_camera_shot_id": candidate_id,
                    "candidate_delivery_window_s": slot["provisional_delivery_window_s"]
                    if basis != "unique_gap_order_colour_display_proposal"
                    else candidate["delivery_window_s"],
                    "association_basis": basis,
                    "physical_throw_identity_verified": False,
                    "exact_release_time_s": None,
                    "exact_settle_time_s": None,
                },
                "video_post_shot_state": {
                    "status": "partial_image_house_observations" if groups else "unobserved",
                    "camera_groups": groups,
                    "complete_sheet_state_verified": False,
                    "metric_rink_coordinates_verified": False,
                },
                "video_physics_simulation_ready": False,
            }
        )
    if len({row["official_shot_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate output slot")
    return rows
