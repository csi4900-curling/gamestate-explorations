"""Short frame-pair registration must preserve motion and abstention."""

import cv2
import numpy as np

from prototype.subframe_camera_registration import composed_residual


def test_composed_registration_separates_camera_shift_and_object_motion():
    rng = np.random.default_rng(171)
    base = np.full((360, 640, 3), 185, np.uint8)
    for x, y in rng.integers([30, 80], [610, 330], size=(240, 2)):
        cv2.circle(base, (int(x), int(y)), 3, (25, 60, 100), -1)
    frames = {
        i / 4: cv2.warpAffine(base, np.float32([[1, 0, 4 * i], [0, 1, -2 * i]]), (640, 360))
        for i in range(5)
    }
    stationary = composed_residual([200, 200], [216, 192], 0, 1, frames.__getitem__)
    moving = composed_residual([200, 200], [229, 192], 0, 1, frames.__getitem__)
    assert stationary["status"] == "all_subpairs_registered"
    assert stationary["camera_residual_px"] < 2
    assert moving["camera_residual_px"] > 10


def test_failed_subpair_abstains_without_stale_transform():
    rng = np.random.default_rng(172)
    image = np.full((360, 640, 3), 185, np.uint8)
    for x, y in rng.integers([30, 80], [610, 330], size=(150, 2)):
        cv2.circle(image, (int(x), int(y)), 3, (25, 60, 100), -1)
    frames = {
        0: image,
        0.25: image.copy(),
        0.5: np.full_like(image, 185),
        0.75: image.copy(),
        1: image.copy(),
    }
    result = composed_residual([200, 200], [200, 200], 0, 1, frames.__getitem__)
    assert result["status"] == "unregistered_subpair"
    assert result["camera_residual_px"] is None
