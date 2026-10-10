import numpy as np

from prototype.highres_underpoint_context import (
    review_tier, underpoint_nonice_fraction)


def test_scaled_underpoint_measures_below_the_body_and_abstains_at_frame_edge():
    frame = np.full((1080, 1920, 3), 230, np.uint8)
    frame[566:680, 900:1020] = (20, 20, 180)
    assert underpoint_nonice_fraction(frame, (960, 500)) > 0.99
    assert underpoint_nonice_fraction(frame, (1200, 500)) == 0
    assert underpoint_nonice_fraction(frame, (960, 1070)) is None


def test_context_middle_range_remains_ambiguous():
    assert review_tier(0.02) == "clear_context_review"
    assert review_tier(0.10) == "ambiguous_context_review"
    assert review_tier(0.30) == "cluttered_context_review"
    assert review_tier(None) == "context_unavailable"
