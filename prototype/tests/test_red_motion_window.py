"""Meaningful edge cases for tentative visual-stop interpretation."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from red_motion_window import split_moving_prefix


def point(t, x, y):
    return {"time_s": t, "center_1080p_px": [x, y]}


def test_stillness_brackets_stop_and_excludes_parked_tail():
    path = [point(0, 0, 100), point(1, 2, 70), point(2, 4, 50),
            point(3, 5, 48), point(4, 5, 48), point(5, 6, 48),
            point(6, 6, 48)]
    result = split_moving_prefix(path)
    assert result["visual_stop_bracket_s"] == [2, 3]
    assert result["observed_moving_prefix_last_s"] == 2
    assert result["stable_confirmation_last_s"] == 5
    assert result["post_stop_tracker_tail_excluded"] == 1


def test_short_pause_then_renewed_motion_does_not_claim_stop():
    path = [point(0, 0, 100), point(1, 0, 70), point(2, 1, 69),
            point(3, 1, 69), point(4, 1, 40)]
    result = split_moving_prefix(path)
    assert result["status"] == "moving_path_right_censored_no_visual_stop"
    assert result["visual_stop_bracket_s"] is None


def test_two_second_gap_does_not_confirm_stationary_identity():
    path = [point(0, 0, 100), point(1, 0, 70), point(3, 0, 70),
            point(4, 0, 70), point(5, 0, 70)]
    result = split_moving_prefix(path)
    assert result["visual_stop_bracket_s"] is None
