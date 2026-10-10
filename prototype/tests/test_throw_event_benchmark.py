import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from throw_event_benchmark import evaluate_events


class ThrowBenchmarkTests(unittest.TestCase):
    def reference(self):
        return [{"id": "E01", "colour": "yellow", "delivery_interval_s": [10, 12]}]

    def prediction(self, id="P01", time=11, colour="yellow"):
        return {"id": id, "crossing_time_s": time, "colour": colour}

    def test_duplicate_near_one_throw_counts_as_false_positive(self):
        score = evaluate_events(
            [self.prediction(), self.prediction("P02", 11.1)], self.reference(), [0, 20]
        )
        self.assertEqual(
            (score["true_positives"], score["false_positives"], score["false_negatives"]), (1, 1, 0)
        )
        self.assertAlmostEqual(score["f1"], 2 / 3)

    def test_wrong_colour_is_visible_after_temporal_match(self):
        score = evaluate_events([self.prediction(colour="red")], self.reference(), [0, 20])
        self.assertEqual(score["true_positives"], 1)
        self.assertEqual(score["colour_errors_among_matches"], 1)
        self.assertEqual(score["colour_aware_true_positives"], 0)
        self.assertEqual(score["colour_aware_false_positives"], 1)
        self.assertEqual(score["colour_aware_false_negatives"], 1)
        self.assertEqual(score["colour_aware_f1"], 0)

    def test_colour_aware_match_uses_correct_candidate_even_when_wrong_one_is_closer(self):
        score = evaluate_events(
            [self.prediction("wrong", 11, "red"), self.prediction("correct", 11.5, "yellow")],
            self.reference(),
            [0, 20],
        )
        self.assertEqual(score["colour_aware_true_positives"], 1)
        self.assertEqual(score["colour_aware_false_positives"], 1)
        self.assertEqual(score["colour_aware_false_negatives"], 0)

    def test_missed_event_and_extra_event(self):
        score = evaluate_events([self.prediction(time=18)], self.reference(), [0, 20])
        self.assertEqual(
            (score["false_positives"], score["false_negatives"], score["f1"]), (1, 1, 0)
        )

    def test_empty_limits(self):
        self.assertEqual(evaluate_events([], [], [0, 20])["f1"], 1)
        self.assertEqual(evaluate_events([], self.reference(), [0, 20])["f1"], 0)
        self.assertEqual(evaluate_events([self.prediction()], [], [0, 20])["f1"], 0)

    def test_overlapping_reference_is_not_a_valid_benchmark(self):
        refs = self.reference() + [{"id": "E02", "colour": "red", "delivery_interval_s": [11, 14]}]
        with self.assertRaises(ValueError):
            evaluate_events([], refs, [0, 20])

    def test_duplicate_prediction_id_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_events([self.prediction(), self.prediction()], self.reference(), [0, 20])

    def test_evidence_interval_can_match_later_confirmation_without_claiming_exact_time(self):
        prediction = self.prediction(time=13)
        prediction["evidence_interval_s"] = [11, 13]
        point_score = evaluate_events([prediction], self.reference(), [0, 20])
        interval_score = evaluate_events(
            [prediction],
            self.reference(),
            [0, 20],
            prediction_time_mode="evidence_interval",
            max_prediction_interval_s=3,
        )
        self.assertEqual(point_score["f1"], 0)
        self.assertEqual(interval_score["f1"], 1)

    def test_evidence_interval_width_is_bounded(self):
        prediction = self.prediction(time=13)
        prediction["evidence_interval_s"] = [1, 13]
        with self.assertRaises(ValueError):
            evaluate_events(
                [prediction],
                self.reference(),
                [0, 20],
                prediction_time_mode="evidence_interval",
                max_prediction_interval_s=3,
            )


if __name__ == "__main__":
    unittest.main()
