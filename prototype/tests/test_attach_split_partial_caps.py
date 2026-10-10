from copy import deepcopy

import pytest

from prototype.attach_split_partial_caps import attach_partial_caps


def fixtures():
    sequence = {
        "source_sha256": "a" * 64,
        "left_candidate_count": 1,
        "limitations": [],
        "rows": [
            {"candidate_id": "left:L1", "left_event_id": "L1",
             "observation_kind": "left_tracked_passage", "observation_time_s": 10,
             "game_state_after": {"complete_board": None, "simulation_ready": False}},
            {"candidate_id": "right:R01:A2", "left_event_id": None,
             "observation_kind": "right_observed_motion_passage", "observation_time_s": 20,
             "game_state_after": {"complete_board": None, "simulation_ready": False}},
        ],
    }
    scan = {"source_sha256": "a" * 64, "rows": [{
        "candidate_id": "left:L1", "left_event_id": "L1",
        "observed_left_passage_time_s": 10,
        "observation_status": "partial_stable_colour_cap_proposals",
        "sample_times_s": [25, 30, 35], "scene_mae_between_samples": [1, 2],
        "coordinate_frame": "source_right_camera_pixels_not_metric",
        "stable_cap_proposals": [{"colour": "red", "pixel_center": [450, 200]}],
        "complete_board_verified": False, "physical_settle_verified": False,
        "simulation_ready": False,
    }]}
    return sequence, scan


def test_attach_keeps_partial_observation_and_unknown_board():
    sequence, scan = fixtures()
    joined = attach_partial_caps(sequence, scan)
    assert joined["stable_cap_proposal_count"] == 1
    assert joined["rows"][0]["post_candidate_partial_cap_observation"][
        "stable_cap_proposals"][0]["colour"] == "red"
    assert joined["rows"][0]["game_state_after"]["complete_board"] is None
    assert joined["rows"][1]["post_candidate_partial_cap_observation"] is None
    assert "post_candidate_partial_cap_observation" not in sequence["rows"][0]


def test_attach_rejects_missing_candidate_and_state_promotion():
    sequence, scan = fixtures()
    scan["rows"] = []
    with pytest.raises(ValueError, match="cover every left"):
        attach_partial_caps(sequence, scan)
    sequence, scan = fixtures()
    scan["rows"][0]["physical_settle_verified"] = True
    with pytest.raises(ValueError, match="promotes physical state"):
        attach_partial_caps(sequence, scan)


def test_attach_rejects_candidate_time_mismatch():
    sequence, scan = fixtures()
    scan = deepcopy(scan)
    scan["rows"][0]["observed_left_passage_time_s"] = 11
    with pytest.raises(ValueError, match="disagrees"):
        attach_partial_caps(sequence, scan)
