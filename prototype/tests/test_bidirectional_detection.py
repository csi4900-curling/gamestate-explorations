"""The diagnostic incoming pass accepts the opposite physical direction."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bidirectional_detection import IncomingPassageDetector
from throw_detection import PassageDetector


class BidirectionalDetectionTests(unittest.TestCase):
    def test_incoming_passage_is_restored_to_original_coordinates(self):
        incoming = IncomingPassageDetector()
        outgoing = PassageDetector()
        for i, y in enumerate(range(80, 39, -4)):
            observation = {
                "colour": "red",
                "pixel": [100.0, float(y)],
                "bbox": [95, y - 4, 10, 8],
                "body_support": 0.8,
            }
            t = i * 0.1
            incoming.update([observation], t)
            outgoing.update([observation], t)
        self.assertEqual(len(outgoing.events), 1)
        self.assertEqual(len(incoming.events), 0)
        incoming = IncomingPassageDetector()
        for i, y in enumerate(range(40, 81, 4)):
            observation = {
                "colour": "red",
                "pixel": [100.0, float(y)],
                "bbox": [95, y - 4, 10, 8],
                "body_support": 0.8,
            }
            incoming.update([observation], i * 0.1)
        self.assertEqual(len(incoming.events), 1)
        self.assertEqual(incoming.events[0]["view_motion"], "positive_y")
        self.assertGreater(incoming.events[0]["velocity_px_s"][1], 0)
        self.assertAlmostEqual(incoming.events[0]["crossing_time_s"], 0.5)
        self.assertAlmostEqual(incoming.events[0]["crossing_x_px"], 100.0)


if __name__ == "__main__":
    unittest.main()
