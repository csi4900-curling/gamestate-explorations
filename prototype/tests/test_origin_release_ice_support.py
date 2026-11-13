import numpy as np

from prototype.origin_release_ice_support import below_ice_fraction, passage_has_ice


def test_white_ice_below_held_cap_passes():
    frame = np.full((360, 640, 3), 240, dtype=np.uint8)
    passage = {"held_center_px": [320, 290]}
    accepted, fraction = passage_has_ice(frame, passage)
    assert accepted and fraction == 1.0


def test_dark_ground_below_held_cap_abstains():
    frame = np.full((360, 640, 3), 240, dtype=np.uint8)
    frame[310:340, 280:360] = 20
    accepted, fraction = passage_has_ice(frame, {"held_center_px": [320, 290]})
    assert not accepted and fraction == 0.0


def test_too_little_visible_below_region_abstains():
    frame = np.full((360, 640, 3), 240, dtype=np.uint8)
    assert below_ice_fraction(frame, [320, 345]) is None
