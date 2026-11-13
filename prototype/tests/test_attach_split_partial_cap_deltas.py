from copy import deepcopy

import pytest

from prototype.attach_split_partial_cap_deltas import attach_deltas


def fixtures():
    sequence = {
        "source_sha256": "a" * 64,
        "left_candidate_count": 1,
        "rows": [
            {
                "candidate_id": "left:L1",
                "left_event_id": "L1",
                "observation_kind": "left_tracked_passage",
                "observation_time_s": 100,
                "post_candidate_partial_cap_observation": {
                    "status": "no_stable_colour_cap_proposals"
                },
                "game_state_after": {"complete_board": None},
            },
            {
                "candidate_id": "right:R01:A2",
                "left_event_id": None,
                "observation_kind": "right_observed_motion_passage",
                "game_state_after": {"complete_board": None},
            },
        ],
    }
    pre = {
        "source_sha256": "a" * 64,
        "rows": [
            {
                "candidate_id": "left:L1",
                "left_event_id": "L1",
                "observed_left_passage_time_s": 100,
                "observation_status": "partial_stable_colour_cap_proposals",
                "sample_times_s": [75, 80, 85],
                "scene_mae_between_samples": [1, 2],
                "coordinate_frame": "source_right_camera_pixels_not_metric",
                "stable_cap_proposals": [{"colour": "red"}],
                "complete_board_verified": False,
            }
        ],
    }
    delta = {
        "source_sha256": "a" * 64,
        "rows": [
            {
                "candidate_id": "left:L1",
                "pre_observation_status": "partial_stable_colour_cap_proposals",
                "post_observation_status": "no_stable_colour_cap_proposals",
                "comparison_status": "partial_cap_image_comparison",
                "image_cap_delta": {"no_longer_observed": ["C01"]},
                "physical_transition_verified": False,
                "complete_board_verified": False,
                "simulation_ready": False,
            }
        ],
    }
    return sequence, pre, delta


def test_attach_keeps_image_delta_without_promoting_board():
    sequence, pre, delta = fixtures()
    joined = attach_deltas(sequence, pre, delta)
    assert joined["rows"][0]["partial_cap_image_transition"]["image_cap_delta"][
        "no_longer_observed"
    ] == ["C01"]
    assert joined["rows"][0]["game_state_after"]["complete_board"] is None
    assert joined["rows"][1]["partial_cap_image_transition"] is None
    assert "partial_cap_image_transition" not in sequence["rows"][0]


def test_attach_rejects_missing_delta_and_physical_promotion():
    sequence, pre, delta = fixtures()
    delta["rows"] = []
    with pytest.raises(ValueError, match="cover every left"):
        attach_deltas(sequence, pre, delta)
    sequence, pre, delta = fixtures()
    delta = deepcopy(delta)
    delta["rows"][0]["physical_transition_verified"] = True
    with pytest.raises(ValueError, match="promotes physical state"):
        attach_deltas(sequence, pre, delta)
