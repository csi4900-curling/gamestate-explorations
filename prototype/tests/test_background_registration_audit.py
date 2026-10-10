import sys
from pathlib import Path
import unittest
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from background_registration_audit import registration_support


class TestBackgroundRegistrationAudit(unittest.TestCase):
    def test_excluding_moving_object_removes_object_dominated_fit(self):
        rng = np.random.default_rng(7)
        first = np.full((360, 640, 3), 225, np.uint8)
        for x, y in rng.integers([300, 150], [370, 220], size=(90, 2)):
            cv2.circle(first, (int(x), int(y)), 2, (0, 0, 200), -1)
        shifted = cv2.warpAffine(first, np.float32([[1, 0, 8], [0, 1, 0]]), (640, 360))
        unmasked = registration_support(first, shifted)
        masked = registration_support(first, shifted, exclude_bbox=[300, 150, 70, 70], margin_px=30)
        self.assertGreaterEqual(unmasked["inliers"], 30)
        self.assertEqual(masked["tracked_features"], 0)
        self.assertFalse(masked["reliable_by_existing_rule"])
