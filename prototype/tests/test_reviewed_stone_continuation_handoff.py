import copy

import pytest

from prototype.reviewed_stone_continuation_handoff import build_continuation_handoff


def fixtures():
    gaps = {
        "rows": [
            {
                "episode_id": "E096",
                "left_motion_candidate_id": "S109",
                "colour_claim": "red",
                "observed_left_motion_path": [1, 2],
                "first_same_colour_local_observation_s": 4584.0,
                "partial_board_local_stones": [
                    {"local_observation_id": "V02", "first_seen_s": 4591.0}
                ],
                "settled_stone_identity_verified": False,
                "simulation_ready": False,
            },
            {
                "episode_id": "E001",
                "left_motion_candidate_id": "S01",
                "colour_claim": "red",
                "observed_left_motion_path": [],
                "first_same_colour_local_observation_s": None,
                "partial_board_local_stones": [],
                "settled_stone_identity_verified": False,
                "simulation_ready": False,
            },
        ]
    }
    caps = {
        "rows": [
            {
                "episode_id": "E096",
                "left_motion_candidate_id": "S109",
                "colour_claim": "red",
                "evaluation_horizon_first_board_time_s": 4584.0,
                "board_blind_continuation_reached_horizon": True,
                "abstention_reason": None,
                "terminal_to_nearest_same_colour_board_center_px_1080": 446.093,
                "any_nearby_same_colour_competitor": False,
                "steps": [1, 2],
                "persistent_stone_identity_verified": False,
                "simulation_ready": False,
            }
        ]
    }
    late = {
        "episode_id": "E096",
        "late_horizon_reached": True,
        "abstention_reason": None,
        "red_board_onset_checkpoints": [
            {
                "board_local_observation_id": "V02",
                "first_seen_s": 4591.0,
                "distances_to_board_red_centers_px_1080": [0.34, 290.203],
            }
        ],
    }
    later = {
        "rows": [
            {
                "episode_id": "E096",
                "continuation_status": "attempted",
                "abstention_reason": None,
                "later_onset_checkpoints": [
                    {
                        "local_observation_id": "V02",
                        "first_seen_s": 4591.0,
                        "tracked_cap_to_onset_detection_px_1080": 0.34,
                    }
                ],
            },
        ]
    }
    return gaps, caps, late, later


def test_preserves_all_rows_and_marks_late_board_link_as_hypothesis():
    rows = build_continuation_handoff(*fixtures())
    assert [r["episode_id"] for r in rows] == ["E096", "E001"]
    assert rows[0]["late_board_link_hypothesis"]["local_board_observation_id"] == "V02"
    assert rows[0]["late_board_link_hypothesis"]["physical_identity_verified"] is False
    assert rows[1]["board_blind_cap_continuation"] is None
    assert all(not r["simulation_ready"] for r in rows)


def test_rejects_missing_cap_coverage():
    gaps, caps, late, later = fixtures()
    caps = copy.deepcopy(caps)
    caps["rows"] = []
    with pytest.raises(ValueError, match="coverage"):
        build_continuation_handoff(gaps, caps, late, later)
