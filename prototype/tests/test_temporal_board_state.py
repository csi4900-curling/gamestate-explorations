from prototype.temporal_board_state import stable_board_stones


def stone(colour, x, y):
    return {"colour": colour, "canonical_lateral_house_radii": x, "longitudinal_house_radii": y}


def test_retains_static_stone_and_rejects_moving_or_single_frame_caps():
    frames = [
        {"time_s": 10, "stones": [stone("yellow", 0.2, -1), stone("red", -0.5, -1.0)]},
        {
            "time_s": 12,
            "stones": [
                stone("yellow", 0.21, -1.01),
                stone("red", -0.5, -0.8),
                stone("yellow", 1, 1),
            ],
        },
        {"time_s": 14, "stones": [stone("yellow", 0.19, -1.0), stone("red", -0.5, -0.6)]},
    ]
    stable = stable_board_stones(frames)
    assert len(stable) == 1
    assert stable[0]["colour"] == "yellow"
    assert stable[0]["supporting_frame_count"] == 3


def test_requires_time_span_even_when_three_frames_agree():
    frames = [{"time_s": t, "stones": [stone("red", 0, 0)]} for t in (10, 11, 12)]
    assert stable_board_stones(frames) == []
