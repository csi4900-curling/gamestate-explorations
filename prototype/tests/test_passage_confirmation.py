import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from passage_confirmation import confirm_passages


def candidate(name, time, velocity, direction="negative_y"):
    return {
        "id": name,
        "crossing_time_s": time,
        "velocity_px_s": [0, velocity],
        "view_motion": direction,
    }


def test_preserves_slow_and_competing_candidates_as_unconfirmed():
    decisions = confirm_passages(
        [
            candidate("slow", 10, -12),
            candidate("stone", 50, -27),
            candidate("duplicate", 56, -22),
        ]
    )
    assert {d["id"]: d["reason"] for d in decisions} == {
        "slow": "below_layout_motion_speed",
        "stone": "motion_speed_supported",
        "duplicate": "competing_passage",
    }


def test_isolated_direction_is_unconfirmed():
    decisions = confirm_passages(
        [
            candidate("a", 10, -25),
            candidate("b", 55, 41, "positive_y"),
            candidate("c", 100, -24),
        ]
    )
    assert decisions[1]["reason"] == "isolated_camera_direction"


def test_positive_run_remains_confirmed():
    decisions = confirm_passages(
        [
            candidate("a", 10, 16, "positive_y"),
            candidate("b", 60, 19, "positive_y"),
            candidate("c", 110, -24),
        ]
    )
    assert [d["status"] for d in decisions] == ["confirmed"] * 3
