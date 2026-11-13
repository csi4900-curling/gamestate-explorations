import pytest

from prototype.game_state_observation import partial_board_observation


def sample():
    return {
        "official_game_code": "GAME",
        "official_shot_id": "GAME-E01-S01",
        "counter_time_s": 100.0,
        "official_symbol_count": 99,
        "comparison": {"matched_count": 0, "unmatched_official": ["secret"]},
        "stable_partial_board": [
            {
                "colour": "yellow",
                "canonical_lateral_house_radii": 0.25,
                "longitudinal_house_radii": -0.5,
                "first_seen_s": 105.0,
                "last_seen_s": 111.0,
                "supporting_frame_count": 4,
                "max_position_spread_house_radii": 0.02,
            }
        ],
    }


def test_export_keeps_video_evidence_partial_and_omits_official_positions():
    result = partial_board_observation(sample(), "a" * 64)
    assert result["observation_interval_s"] == [105.0, 111.0]
    assert result["stones"][0]["position_house_radii"] == [0.25, -0.5]
    assert result["completeness"] == "unknown_from_video"
    assert result["simulation_ready"] is False
    assert "comparison" not in str(result)
    assert "secret" not in str(result)


def test_empty_or_invalid_board_is_not_promoted():
    row = sample()
    row["stable_partial_board"] = []
    assert partial_board_observation(row, "a" * 64) is None
    row = sample()
    row["stable_partial_board"][0]["supporting_frame_count"] = 1
    with pytest.raises(ValueError):
        partial_board_observation(row, "a" * 64)
