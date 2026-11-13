"""Left image observations enrich, but never promote, candidate game state."""

import pytest

from candidate_state_handoff_v2 import attach_left_candidate_boards


def fixture():
    handoff = {
        "source_sha256": "source",
        "input_sha256": {"candidate_review_union": "union"},
        "limitations": [
            "Left proposals have no board observation from this right-only sampling stage."
        ],
        "ordered_candidates": [
            {
                "candidate_id": "R01-S1",
                "origin": "left_routed_proposal",
                "source_run_id": "R01",
                "source_time_s": 10,
                "observed_motion_interval_s": [9, 11],
                "post_candidate_image_observation": {
                    "status": "not_sampled_by_right_only_board_stage"
                },
                "game_state_after": {"complete_board": None, "simulation_ready": False},
            },
            {
                "candidate_id": "RIGHT-I01:R1",
                "origin": "right_entry_review",
                "source_time_s": 20,
                "post_candidate_image_observation": {
                    "status": "partial_stable_colour_cap_proposals"
                },
                "game_state_after": {"complete_board": None, "simulation_ready": False},
            },
        ],
    }
    boards = {
        "source_sha256": "source",
        "input_sha256": {"candidate_review_union": "union"},
        "split_run_ids": ["R01"],
        "rows": [
            {
                "candidate_id": "R01-S1",
                "source_time_s": 10,
                "observed_motion_interval_s": [9, 11],
                "next_candidate_time_s": 20,
                "observation_status": "abstain_next_candidate_or_route_boundary",
                "anchor_stability_agreement": None,
                "coordinate_frame": "right_pixels",
                "stable_cap_proposals": [],
                "sample_frames": [],
                "complete_board_verified": False,
                "physical_settle_verified": False,
                "persistent_stone_identity_verified": False,
                "simulation_ready": False,
            },
        ],
    }
    return handoff, boards


def test_left_abstention_attaches_and_right_board_remains():
    result = attach_left_candidate_boards(*fixture())
    left, right = result["ordered_candidates"]
    assert (
        left["post_candidate_image_observation"]["status"]
        == "abstain_next_candidate_or_route_boundary"
    )
    assert (
        right["post_candidate_image_observation"]["status"] == "partial_stable_colour_cap_proposals"
    )
    assert all(
        row["game_state_after"]["complete_board"] is None
        and not row["game_state_after"]["simulation_ready"]
        for row in result["ordered_candidates"]
    )


def test_missing_left_row_or_promoted_state_rejected():
    handoff, boards = fixture()
    boards["rows"] = []
    with pytest.raises(ValueError, match="do not cover"):
        attach_left_candidate_boards(handoff, boards)
    handoff, boards = fixture()
    boards["rows"][0]["complete_board_verified"] = True
    with pytest.raises(ValueError, match="promotes physical state"):
        attach_left_candidate_boards(handoff, boards)
