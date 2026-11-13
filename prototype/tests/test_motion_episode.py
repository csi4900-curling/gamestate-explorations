import pytest

from prototype.motion_episode import stationary_to_motion_episode


def point(t, x, y):
    return {"time_s": t, "pixel": [x, y]}


def test_finds_motion_after_stable_prefix_without_calling_it_release():
    stationary = [point(i / 10, 50, 100 + (i % 2) * 0.5) for i in range(15)]
    moving = [point(1.5 + i / 10, 50, 100 - i * 4) for i in range(8)]
    result = stationary_to_motion_episode(stationary + moving, 1.9, "negative_y")
    assert result is not None
    assert result["onset_time_s"] == 1.6
    assert result["moving_longitudinal_span_px"] >= 20
    assert "not_release" in result["interpretation"]


def test_does_not_invent_transition_for_continuous_motion():
    points = [point(i / 10, 50, 100 - i * 3) for i in range(22)]
    assert stationary_to_motion_episode(points, 1.1, "negative_y") is None


def test_validates_direction_and_order():
    points = [point(i / 10, 50, 100) for i in range(8)]
    with pytest.raises(ValueError, match="Direction"):
        stationary_to_motion_episode(points, 0.5, "up")
    with pytest.raises(ValueError, match="increase"):
        stationary_to_motion_episode(points[:4] + points[3:], 0.5, "positive_y")
