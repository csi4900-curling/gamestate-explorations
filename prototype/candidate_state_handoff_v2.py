"""Add left-proposal board observations without promoting candidate game state."""

from collections import Counter
from copy import deepcopy


def attach_left_candidate_boards(handoff, left_scan):
    if handoff["source_sha256"] != left_scan["source_sha256"]:
        raise ValueError("Handoff and left board sources differ")
    if (
        handoff["input_sha256"]["candidate_review_union"]
        != left_scan["input_sha256"]["candidate_review_union"]
    ):
        raise ValueError("Handoff and left boards use different candidate ledgers")
    boards = {row["candidate_id"]: row for row in left_scan["rows"]}
    if len(boards) != len(left_scan["rows"]):
        raise ValueError("Duplicate left candidate board observation")
    rows = deepcopy(handoff["ordered_candidates"])
    split_run_ids = set(left_scan["split_run_ids"])
    left_candidates = {
        row["candidate_id"]
        for row in rows
        if row["origin"] == "left_routed_proposal" and row.get("source_run_id") in split_run_ids
    }
    if set(boards) != left_candidates:
        raise ValueError("Left candidate board observations do not cover left motion rows")
    for row in rows:
        board = boards.get(row["candidate_id"])
        if board is None:
            continue
        if (
            row["source_time_s"] != board["source_time_s"]
            or row["observed_motion_interval_s"] != board["observed_motion_interval_s"]
            or board["complete_board_verified"]
            or board["physical_settle_verified"]
            or board["persistent_stone_identity_verified"]
            or board["simulation_ready"]
        ):
            raise ValueError("Left observation disagrees or promotes physical state")
        row["post_candidate_image_observation"] = {
            "status": board["observation_status"],
            "observed_motion_interval_s": board["observed_motion_interval_s"],
            "next_candidate_time_s": board["next_candidate_time_s"],
            "anchor_stability_agreement": board["anchor_stability_agreement"],
            "coordinate_frame": board["coordinate_frame"],
            "stable_cap_proposals": board["stable_cap_proposals"],
            "sample_times_s": [sample["time_s"] for sample in board["sample_frames"]],
            "complete_board_verified": False,
            "physical_settle_verified": False,
            "persistent_stone_identity_verified": False,
        }
    result = deepcopy(handoff)
    result["status"] = "all_split_candidate_partial_image_observations_not_game_state"
    result["ordered_candidates"] = rows
    result["image_observation_status_counts"] = dict(
        Counter(row["post_candidate_image_observation"]["status"] for row in rows)
    )
    result["limitations"] = [
        item
        for item in handoff["limitations"]
        if item != "Left proposals have no board observation from this right-only sampling stage."
    ] + [
        "Left proposals now have guarded right-view cap samples or explicit abstentions.",
        "Post-candidate image caps do not verify a delivered stone or a complete game state.",
    ]
    return result
