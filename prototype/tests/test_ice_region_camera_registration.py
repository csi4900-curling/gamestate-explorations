"""Ice-region camera registration admits wide rink and abstains off-rink."""

import cv2
import numpy as np

from prototype.ice_region_camera_registration import (
    ice_region_composed_residual,
    largest_ice_like_region,
)


def test_wide_ice_region_composes_camera_shift():
    rng = np.random.default_rng(24)
    base = np.full((360, 640, 3), (190, 190, 190), np.uint8)
    for x, y in rng.integers([30, 80], [610, 330], size=(240, 2)):
        cv2.circle(base, (int(x), int(y)), 3, (100, 160, 170), -1)
    frames = {
        i / 4: cv2.warpAffine(base, np.float32([[1, 0, 4 * i], [0, 1, -2 * i]]), (640, 360))
        for i in range(5)
    }
    result = ice_region_composed_residual([200, 200], [216, 192], 0, 1, frames.__getitem__)
    assert result["status"] == "all_ice_region_subpairs_registered"
    assert result["camera_residual_px"] < 2


def test_small_bright_foreground_is_not_a_rink_region():
    frame = np.full((360, 640, 3), (45, 45, 45), np.uint8)
    cv2.rectangle(frame, (230, 160), (360, 260), (225, 225, 225), -1)
    mask, fraction = largest_ice_like_region(frame)
    assert mask is None
    assert fraction < 0.20
