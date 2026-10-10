from prototype.right_motion_onset import observed_quiet_to_motion


def points(ys):
    return [{"time_s": float(t), "pixel": [400.0, float(y)]} for t, y in enumerate(ys)]


def test_bounds_quiet_to_sustained_motion_without_claiming_release():
    result = observed_quiet_to_motion(
        points([100, 100, 100, 100, 100, 120, 145, 170]), "positive_y"
    )
    assert result["onset_bracket_s"] == [4.0, 5.0]
    assert result["supporting_step_rates_px_s"] == [20.0, 25.0]
    assert result["last_observed_track_time_s"] == 7.0
    assert result["physical_release_time_s"] is None
    assert result["physical_settle_time_s"] is None


def test_gradual_acceleration_widens_onset_bracket():
    result = observed_quiet_to_motion(
        points([100, 100, 100, 100, 106, 116, 136, 160]), "positive_y"
    )
    assert result["onset_bracket_s"] == [3.0, 6.0]


def test_moving_person_and_wrong_direction_are_not_classified_as_stones():
    moving_person = observed_quiet_to_motion(
        points([100, 100, 100, 100, 100, 120, 145]), "positive_y"
    )
    assert moving_person["status"] == "observed_quiet_to_sustained_directional_motion"
    assert moving_person["physical_stone_identity_verified"] is False
    assert (
        observed_quiet_to_motion(points([100, 100, 100, 100, 100, 120, 145]), "negative_y")[
            "status"
        ]
        == "no_supported_quiet_to_motion_transition"
    )
