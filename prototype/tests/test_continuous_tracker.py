import unittest, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from continuous_tracker import Tracker


def detection(x=10, colour="red"):
    return {"colour": colour, "pixel_center": [x, 20]}


class TrackingTests(unittest.TestCase):
    def test_missing_not_emitted_and_expired_identity_not_reused(self):
        t = Tracker()
        first = t.update([detection()], 0)[0]["track_id"]
        self.assertEqual(t.update([], 0.5), [])
        self.assertNotEqual(t.update([detection()], 2)[0]["track_id"], first)

    def test_one_to_one_and_colour(self):
        t = Tracker()
        t.update([detection()], 0)
        out = t.update([detection(11), detection(12), detection(11, "yellow")], 0.5)
        self.assertEqual(len({s["track_id"] for s in out}), 3)
        self.assertEqual(out[0]["track_id"], 1)

    def test_stability_requires_temporal_evidence(self):
        t = Tracker()
        for i in range(5):
            out = t.update([detection()], i * 0.5)[0]
        self.assertEqual(out["motion_status"], "visually_stable")
        self.assertEqual(
            t.update([detection(40)], 2.5)[0]["motion_status"], "moving_or_insufficient_history"
        )


if __name__ == "__main__":
    unittest.main()
