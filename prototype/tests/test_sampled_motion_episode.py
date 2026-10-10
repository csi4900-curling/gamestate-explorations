import pytest

from prototype.sampled_motion_episode import sustained_motion_episode


def p(t, y):
    return {"time_s": t, "center_1080p_px": [100, y]}


def test_splits_long_still_prefix_before_downward_moving_episode():
    points = [p(t, 500) for t in range(20)] + [p(20, 550), p(21, 620), p(22, 700)]
    episode = sustained_motion_episode(points)
    assert episode["direction"] == "positive_y"
    assert episode["motion_onset_observation_bracket_s"] == [19, 20]
    assert episode["pre_onset_observation_count"] == 19
    assert episode["physical_release_verified"] is False


def test_accepts_upward_motion_without_stationary_prefix():
    episode = sustained_motion_episode([p(5, 900), p(6, 840), p(7, 780)])
    assert episode["direction"] == "negative_y"
    assert episode["pre_onset_observed_interval_s"] is None


def test_rejects_jitter_and_gapped_motion():
    assert sustained_motion_episode([p(0, 500), p(1, 504), p(2, 501), p(3, 500)]) is None
    assert sustained_motion_episode([p(0, 500), p(2, 550), p(4, 620)]) is None


def test_rejects_nonmonotonic_times():
    with pytest.raises(ValueError, match="increase"):
        sustained_motion_episode([p(0, 500), p(1, 450), p(1, 400)])
