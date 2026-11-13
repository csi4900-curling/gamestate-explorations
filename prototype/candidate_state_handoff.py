"""Attach partial right-view image observations to an ordered candidate ledger."""

from collections import Counter


def attach_candidate_states(union, right_boards):
    if union["source_sha256"] != right_boards["source_sha256"]:
        raise ValueError("Candidate and board observation sources differ")
    board_by_id = {row["right_entry_id"]: row for row in right_boards["rows"]}
    if len(board_by_id) != len(right_boards["rows"]):
        raise ValueError("Duplicate right-entry board observation")
    right_rows = [row for row in union["candidates"] if row["origin"] == "right_entry_review"]
    if any(len(row["right_entry_ids"]) != 1 for row in right_rows):
        raise ValueError("Right-only candidate must refer to one entry")
    right_candidates = {row["right_entry_ids"][0]: row["candidate_id"] for row in right_rows}
    if len(right_candidates) != len(right_rows):
        raise ValueError("Duplicate right-only candidate entry ID")
    if set(board_by_id) != set(right_candidates):
        raise ValueError("Right-only review and board observation IDs differ")
    rows = []
    for candidate in union["candidates"]:
        row = dict(candidate)
        if candidate["origin"] == "right_entry_review":
            board = board_by_id[candidate["right_entry_ids"][0]]
            row["post_candidate_image_observation"] = {
                "status": board["observation_status"],
                "entry_time_s": board["entry_time_s"],
                "entry_time_bracket_s": board["entry_time_bracket_s"],
                "anchor_stability_agreement": board["anchor_stability_agreement"],
                "coordinate_frame": board["coordinate_frame"],
                "stable_cap_proposals": board["stable_cap_proposals"],
                "sample_times_s": [frame["time_s"] for frame in board["sample_frames"]],
                "complete_board_verified": False,
                "physical_settle_verified": False,
                "persistent_stone_identity_verified": False,
            }
        else:
            row["post_candidate_image_observation"] = {
                "status": "not_sampled_by_right_only_board_stage",
                "stable_cap_proposals": [],
                "complete_board_verified": False,
                "physical_settle_verified": False,
                "persistent_stone_identity_verified": False,
            }
        row["game_state_after"] = {
            "end_identity": None,
            "official_shot_identity": None,
            "release_time_s": None,
            "settle_time_s": None,
            "complete_board": None,
            "persistent_stone_ids": None,
            "metric_trajectory": None,
            "spin_revolution_count": None,
            "simulation_ready": False,
        }
        rows.append(row)
    return {
        "status": "candidate_to_partial_image_state_not_complete_game_state",
        "source_id": union["source_id"],
        "source_sha256": union["source_sha256"],
        "source_interval_s": union["source_interval_s"],
        "candidate_count": len(rows),
        "image_observation_status_counts": dict(
            Counter(row["post_candidate_image_observation"]["status"] for row in rows)
        ),
        "physical_throw_count_verified": None,
        "complete_game_state_count_verified": 0,
        "simulation_ready_count": 0,
        "ordered_candidates": rows,
        "limitations": [
            "Candidate order is not a verified physical throw order; duplicates and nonstones remain possible.",
            "Colour-cap sets are image-local partial observations, not complete physical boards.",
            "Left proposals have no board observation from this right-only sampling stage.",
            "No cross-event cap identity or state transition is inferred from these rows.",
        ],
    }
