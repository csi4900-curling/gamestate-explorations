"""A continuous moving cap must survive; identity jumps must not simulate one."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from learned_gap_confirmation import longest_smooth_motion_run


def test_continuous_moving_cap_passes_fallback_support():
    points = [
        {"time_s": round(i * 0.2, 1), "pixel": [100 + 6 * i, 120]}
        for i in range(16)
    ]
    quality = longest_smooth_motion_run(points)
    assert quality["smooth_run_duration_s"] == 3.0
    assert quality["smooth_run_moving_steps"] == 15


def test_distant_identity_jumps_do_not_accumulate_as_smooth_motion():
    points = [
        {"time_s": round(i * 0.2, 1), "pixel": [100 + 6 * i + 100 * (i // 5), 120]}
        for i in range(20)
    ]
    quality = longest_smooth_motion_run(points)
    assert quality["smooth_run_duration_s"] < 2.0
    assert quality["smooth_run_moving_steps"] < 8
