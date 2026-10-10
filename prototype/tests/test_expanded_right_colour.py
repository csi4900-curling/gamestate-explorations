import unittest

import cv2
import numpy as np

from expanded_right_colour import expanded_right_colour_proposals
from scripts.probe_static_left_right_cap_motion import right_colour_proposals


class ExpandedRightColourTests(unittest.TestCase):
    def test_near_camera_larger_cap_is_only_in_diagnostic_roi(self):
        frame = np.full((360, 640, 3), 235, dtype=np.uint8)
        cv2.ellipse(frame, (460, 341), (9, 6), 0, 0, 360,
                    (0, 210, 240), -1)
        self.assertEqual(right_colour_proposals(frame)["yellow"], [])
        found = expanded_right_colour_proposals(frame)["yellow"]
        self.assertEqual(len(found), 1)
        self.assertGreater(found[0]["pixel"][1], 325)


if __name__ == "__main__":
    unittest.main()
