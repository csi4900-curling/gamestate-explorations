import unittest, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from throw_detection import PassageDetector
from shot_intent import final_position_error
from evaluate_throws import evaluate


class PassageTests(unittest.TestCase):
    def run_path(self, ys):
        d = PassageDetector()
        for i, y in enumerate(ys):
            d.update([{"colour": "red", "pixel": [150, y], "bbox": [145, y - 3, 10, 6]}], i * 0.1)
        return d

    def test_stationary_not_throw(self):
        self.assertEqual(self.run_path([80] * 80).events, [])

    def test_reverse_direction_not_outgoing(self):
        self.assertEqual(self.run_path(list(range(20, 100, 2))).events, [])

    def test_one_passage_emits_once(self):
        self.assertEqual(len(self.run_path(list(range(100, 0, -2))).events), 1)

    def test_teleport_not_throw(self):
        self.assertEqual(self.run_path([100] * 10 + [20] * 10).events, [])

    def test_missing_observations_not_filled(self):
        d = self.run_path([95, 93, 91])
        d.update([], 4)
        self.assertEqual(d.events, [])


class EventEvaluationTests(unittest.TestCase):
    def test_duplicate_is_false_positive(self):
        r = [{"id": "r", "colour": "red", "crossing_interval_s": [10, 11]}]
        e = [{"id": str(i), "colour": "red", "crossing_time_s": 10.5} for i in range(2)]
        result = evaluate(e, r)
        self.assertEqual(result["true_positives"], 1)
        self.assertEqual(result["false_positives"], 1)

    def test_colour_error_not_hidden(self):
        result = evaluate(
            [{"id": "e", "colour": "yellow", "crossing_time_s": 10.5}],
            [{"id": "r", "colour": "red", "crossing_interval_s": [10, 11]}],
        )
        self.assertEqual(result["true_positives"], 1)
        self.assertEqual(result["colour_correct"], 0)

    def test_late_prediction_miss_and_false_positive(self):
        result = evaluate(
            [{"id": "e", "colour": "red", "crossing_time_s": 30}],
            [{"id": "r", "colour": "red", "crossing_interval_s": [10, 11]}],
        )
        self.assertEqual((result["misses"], result["false_positives"]), (1, 1))


class IntentTests(unittest.TestCase):
    def setUp(self):
        self.intent = {
            "kind": "resting_destination",
            "reviewed": True,
            "evidence": "frame:12",
            "shot_type": "draw",
            "coordinate_frame": "tee-m",
            "position_m": [0, 0],
        }
        self.outcome = {
            "settled": True,
            "interaction_detected": False,
            "coordinate_frame": "tee-m",
            "position_m": [0.3, 0.4],
        }

    def test_known_distance(self):
        self.assertAlmostEqual(final_position_error(self.intent, self.outcome)["error_m"], 0.5)

    def test_aiming_broom_cannot_be_scored(self):
        self.intent["kind"] = "aiming_broom_candidate"
        self.assertIsNone(final_position_error(self.intent, self.outcome)["error_m"])

    def test_collision_cannot_use_draw_distance(self):
        self.outcome["interaction_detected"] = True
        self.assertIsNone(final_position_error(self.intent, self.outcome)["error_m"])

    def test_unknown_interaction_status_rejected(self):
        self.outcome.pop("interaction_detected")
        self.assertIsNone(final_position_error(self.intent, self.outcome)["error_m"])

    def test_mismatched_camera_frames_rejected(self):
        self.outcome["coordinate_frame"] = "other-camera"
        self.assertIsNone(final_position_error(self.intent, self.outcome)["error_m"])

    def test_unreviewed_destination_rejected(self):
        self.intent["reviewed"] = False
        self.assertIsNone(final_position_error(self.intent, self.outcome)["error_m"])


if __name__ == "__main__":
    unittest.main()
