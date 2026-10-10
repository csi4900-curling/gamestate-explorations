import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from throw_event_screening import appearance_at_crossing


class AppearanceScreeningTests(unittest.TestCase):
    def test_unreadable_video_does_not_create_a_stone_event(self):
        event = {"crossing_time_s": 1.0, "trajectory": []}
        with self.assertRaises(ValueError):
            appearance_at_crossing(event, cv2.VideoCapture("/nonexistent.mp4"), 30)

    def test_bright_and_dark_candidate_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            video = Path(folder) / "proposals.mp4"
            writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"mp4v"), 10, (640, 360))
            self.assertTrue(writer.isOpened())
            for _ in range(20):
                frame = np.full((360, 640, 3), 170, dtype=np.uint8)
                frame[10:15, 10:20] = (0, 0, 180)
                frame[10:15, 40:50] = (0, 0, 45)
                writer.write(frame)
            writer.release()
            cap = cv2.VideoCapture(str(video))
            bright = {
                "crossing_time_s": 1.0,
                "trajectory": [{"time_s": 1.0, "bbox": [10, 10, 10, 10]}],
            }
            dark = {
                "crossing_time_s": 1.0,
                "trajectory": [{"time_s": 1.0, "bbox": [40, 10, 10, 10]}],
            }
            self.assertEqual(
                appearance_at_crossing(bright, cap, 10)["status"], "stone_appearance_candidate"
            )
            self.assertEqual(
                appearance_at_crossing(dark, cap, 10)["status"], "person_or_other_object_suspected"
            )
            cap.release()


if __name__ == "__main__":
    unittest.main()
