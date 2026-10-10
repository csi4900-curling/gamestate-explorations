import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from registration_hold import ice_similarity


def test_identical_ice_accepts_but_large_shift_rejects():
    image = np.full((1080, 1920, 3), 240, np.uint8)
    cv2.line(image, (1010, 850), (1880, 850), (30, 40, 50), 4)
    cv2.circle(image, (1450, 700), 40, (80, 90, 100), 5)
    assert ice_similarity(image, image)["accepted"]
    shifted = np.roll(image, 20, axis=1)
    assert not ice_similarity(shifted, image)["accepted"]
