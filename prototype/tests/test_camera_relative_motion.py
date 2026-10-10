"""Camera translation must be removed before judging object movement."""

import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from camera_relative_motion import (
    estimate_camera_transform,
    longest_relative_motion_run,
    residual_motion,
)


def test_static_point_tracks_camera_shift_while_independent_motion_remains():
    rng = np.random.default_rng(28)
    image = np.full((360, 640, 3), 180, np.uint8)
    for x, y in rng.integers([10, 80], [630, 350], size=(180, 2)):
        cv2.circle(image, (int(x), int(y)), 3, (40, 70, 120), -1)
    shifted = cv2.warpAffine(image, np.float32([[1, 0, 12], [0, 1, -7]]), (640, 360))
    motion = estimate_camera_transform(image, shifted)
    assert motion is not None and motion["reliable"]
    assert residual_motion([200, 200], [212, 193], motion) < 2
    assert residual_motion([200, 200], [222, 193], motion) > 8


def test_unreliable_pair_breaks_motion_run():
    rows = [
        {"interval_s": [0, 1], "camera_residual_px": 9},
        {"interval_s": [1.2, 2.2], "camera_residual_px": 10},
        {"interval_s": [2.4, 3.4], "camera_residual_px": None},
        {"interval_s": [3.6, 4.6], "camera_residual_px": 12},
    ]
    assert longest_relative_motion_run(rows) == 2
