"""Short transit must reject jitter while retaining brief coherent motion."""

import pytest

from short_cap_transit import short_transits


def point(x, y=300, score=0.5):
    return {"pixel": [x, y], "patch_score": score}


def test_short_fast_stone_passes():
    rows = [(0.0, [point(300)]), (0.2, [point(322)]), (0.4, [point(347)]), (0.6, [point(375)])]
    tracks = short_transits(rows)
    assert len(tracks) == 1
    assert tracks[0]["point_count"] == 4
    assert tracks[0]["displacement_px"] == 75


def test_stationary_and_zigzag_patches_do_not_pass():
    stationary = [(i * 0.2, [point(300 + i % 2)]) for i in range(8)]
    zigzag = [(0.0, [point(300)]), (0.2, [point(345)]), (0.4, [point(305)]), (0.6, [point(350)])]
    assert short_transits(stationary) == []
    assert short_transits(zigzag) == []


def test_duplicate_time_is_invalid():
    with pytest.raises(ValueError):
        short_transits([(1.0, []), (1.0, [])])
