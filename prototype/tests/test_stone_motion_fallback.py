import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from stone_motion_fallback import (
    moving_cap_tracks,
    stone_cap_candidates,
    verify_stone_motion_in_interval,
)


class FrameCapture:
    def __init__(self, frames):
        self.frames = frames
        self.index = 0

    def set(self, _property, position):
        self.index = int(position)

    def read(self):
        return True, self.frames[self.index]


class StoneMotionFallbackTests(unittest.TestCase):
    def frame(self, stone_x=None):
        frame = np.full((360, 640, 3), 240, dtype=np.uint8)
        cv2.circle(frame, (100, 210), 6, (0, 0, 190), -1)  # Red painted dot, no granite.
        if stone_x is not None:
            cv2.circle(frame, (stone_x, 210), 12, (140, 140, 140), -1)
            cv2.circle(frame, (stone_x, 207), 6, (0, 0, 190), -1)
        return frame

    def test_granite_surround_and_motion_reject_static_red_paint(self):
        observations = []
        for t, x in enumerate((200, 210, 220, 230, 240)):
            candidates = stone_cap_candidates(self.frame(x), "red")
            self.assertEqual(len(candidates), 1)
            self.assertAlmostEqual(candidates[0]["pixel"][0], x, delta=1)
            observations.append((float(t), candidates))
        tracks = moving_cap_tracks(observations)
        self.assertEqual(len(tracks), 1)
        self.assertEqual(len(tracks[0]["points"]), 5)
        self.assertGreaterEqual(tracks[0]["span_px"], 40)

    def test_stationary_stone_is_not_a_moving_delivery(self):
        observations = [(float(t), stone_cap_candidates(self.frame(200), "red")) for t in range(5)]
        self.assertEqual(moving_cap_tracks(observations), [])

    def test_nearby_stone_does_not_join_track_after_large_jump(self):
        observations = [
            (float(t), [{"pixel": [float(x), 200.0]}])
            for t, x in ((0, 100), (1, 110), (2, 120), (3, 130), (5, 215))
        ]
        tracks = moving_cap_tracks(observations)
        self.assertEqual(len(tracks), 1)
        self.assertEqual(len(tracks[0]["points"]), 4)
        self.assertEqual(tracks[0]["span_px"], 30)

    def test_interval_verification_requires_a_unique_moving_stone(self):
        frames = [self.frame(x) for x in (200, 210, 220, 230, 240)]
        evidence = verify_stone_motion_in_interval(
            FrameCapture(frames), 1, colour="red", start_s=0, end_s=5
        )
        self.assertEqual(evidence["search_interval_s"], [0, 5])
        self.assertIsNotNone(evidence["selected_track"])

        ambiguous_frames = []
        for x in (200, 210, 220, 230, 240):
            frame = self.frame(x)
            cv2.circle(frame, (x + 150, 250), 12, (140, 140, 140), -1)
            cv2.circle(frame, (x + 150, 247), 6, (0, 0, 190), -1)
            ambiguous_frames.append(frame)
        ambiguous = verify_stone_motion_in_interval(
            FrameCapture(ambiguous_frames), 1, colour="red", start_s=0, end_s=5
        )
        self.assertEqual(len(ambiguous["tracks"]), 2)
        self.assertIsNone(ambiguous["selected_track"])

    def test_hard_cut_splits_pixel_continuous_track(self):
        frames = []
        for t in range(8):
            x = 200 + 10 * t
            frame = self.frame(x)
            if t >= 4:
                frame[:] = (255, 0, 0)
                frame[:, 150:320] = 240
                cv2.circle(frame, (x, 210), 12, (140, 140, 140), -1)
                cv2.circle(frame, (x, 207), 6, (0, 0, 190), -1)
            frames.append(frame)
        uncut = verify_stone_motion_in_interval(
            FrameCapture(frames), 1, colour="red", start_s=0, end_s=8
        )
        cut_aware = verify_stone_motion_in_interval(
            FrameCapture(frames), 1, colour="red", start_s=0, end_s=8, detect_hard_cuts=True
        )
        self.assertEqual(len(uncut["tracks"]), 1)
        self.assertEqual(cut_aware["hard_cut_times_s"], [4.0])
        self.assertEqual(len(cut_aware["tracks"]), 2)
        self.assertIsNone(cut_aware["selected_track"])


if __name__ == "__main__":
    unittest.main()
