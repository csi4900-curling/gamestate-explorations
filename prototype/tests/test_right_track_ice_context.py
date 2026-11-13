"""Ice-context measurement excludes the tracked coloured centre."""

import numpy as np

from right_track_ice_context import nonice_ring_fraction, three_sample_context


def test_white_surround_isolated_even_with_coloured_center():
    frame = np.full((360, 640, 3), 240, dtype=np.uint8)
    frame[175:185, 315:325] = [0, 0, 255]
    assert nonice_ring_fraction(frame, [320, 180]) == 0


def test_nonice_context_is_detected_and_three_samples_use_median():
    white = np.full((360, 640, 3), 240, dtype=np.uint8)
    dark = white.copy()
    dark[140:220, 292:348] = 0
    assert nonice_ring_fraction(dark, [320, 180]) == 1
    points = [{"pixel": [320, 180]}] * 3
    score = three_sample_context([white, dark, dark], points)
    assert score["median_nonice_ring_fraction"] == 1
    assert not score["physical_stone_identity_verified"]
