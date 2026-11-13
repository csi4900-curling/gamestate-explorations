"""A partial image observation cannot become a complete game state."""

import pytest

from candidate_state_handoff import attach_candidate_states


def fixture():
    union = {
        "source_id": "match",
        "source_sha256": "source",
        "source_interval_s": [0, 100],
        "candidates": [
            {
                "candidate_id": "R01-S01",
                "origin": "left_routed_proposal",
                "right_entry_ids": [],
                "source_time_s": 10,
            },
            {
                "candidate_id": "RIGHT-I01:R001",
                "origin": "right_entry_review",
                "right_entry_ids": ["I01:R001"],
                "source_time_s": 30,
            },
        ],
    }
    boards = {
        "source_sha256": "source",
        "rows": [
            {
                "right_entry_id": "I01:R001",
                "observation_status": "abstain_entry_time_sensitive",
                "entry_time_s": 30,
                "entry_time_bracket_s": [29, 31],
                "anchor_stability_agreement": False,
                "coordinate_frame": "full_source_right_camera_pixels_not_metric",
                "stable_cap_proposals": [],
                "sample_frames": [],
            },
        ],
    }
    return union, boards


def test_abstention_survives_and_all_physical_state_remains_unknown():
    result = attach_candidate_states(*fixture())
    assert result["candidate_count"] == 2
    assert (
        result["ordered_candidates"][0]["post_candidate_image_observation"]["status"]
        == "not_sampled_by_right_only_board_stage"
    )
    assert (
        result["ordered_candidates"][1]["post_candidate_image_observation"]["status"]
        == "abstain_entry_time_sensitive"
    )
    assert all(
        row["game_state_after"]["complete_board"] is None
        and not row["game_state_after"]["simulation_ready"]
        for row in result["ordered_candidates"]
    )


def test_unmatched_right_board_is_rejected():
    union, boards = fixture()
    boards["rows"][0]["right_entry_id"] = "I01:R002"
    with pytest.raises(ValueError, match="IDs differ"):
        attach_candidate_states(union, boards)
