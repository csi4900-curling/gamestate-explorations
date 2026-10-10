import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from end_evaluation import evaluate_end, validate_reference


class EndEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.board = dict(
            id="B01",
            throw_id="E01",
            time_s=20,
            complete=True,
            coordinate_frame="source_pixels",
            units="px",
            reference_method="independent_human_image_clicks",
            stones=[dict(colour="red", position=[10, 10], identity="stone1")],
        )
        self.ref = dict(
            schema=1,
            reviewer="Human",
            independent=True,
            complete_end_reviewed=True,
            source_sha256="test",
            source_interval_s=[0, 30],
            events=[
                dict(id="E01", colour="red", delivery_interval_s=[5, 10], arrival_identity="stone1")
            ],
            boards=[self.board],
        )
        self.pred = dict(
            source_sha256="test",
            source_interval_s=[0, 30],
            events=[dict(id="P01", colour="red", crossing_time_s=7, arrival_identity="stone1")],
            boards=[copy.deepcopy(self.board)],
            identity_correspondence={"method": "reviewed_source_link",
                                     "prediction_to_reference": {"stone1": "stone1"}},
        )

    def test_missing_outputs_are_failures(self):
        self.pred.update(events=[], boards=[])
        r = evaluate_end(self.ref, self.pred)
        self.assertEqual(r["events"]["misses"], 1)
        self.assertEqual((r["events"]["precision"], r["events"]["recall"],
                          r["events"]["f1"]), (0, 0, 0))
        self.assertEqual(r["boards"]["complete_correct_fraction"], 0)
        self.assertEqual(r["cross_view_identity"]["coverage"], 0)

    def test_duplicate_event_counts_extra(self):
        self.pred["events"].append(dict(self.pred["events"][0], id="P02"))
        result = evaluate_end(self.ref, self.pred)["events"]
        self.assertEqual(result["extras"], 1)
        self.assertEqual((result["precision"], result["recall"], result["f1"]),
                         (0.5, 1.0, 2 / 3))

    def test_wrong_colour_not_hidden_by_matching(self):
        self.pred["events"][0]["colour"] = "yellow"
        result = evaluate_end(self.ref, self.pred)["events"]
        self.assertEqual(result["colour_errors"], 1)
        self.assertEqual(result["f1"], 1)
        self.assertEqual(result["colour_aware_f1"], 0)

    def test_wrong_identity_cannot_pass_board(self):
        self.pred["boards"][0]["stones"][0]["identity"] = "stone2"
        self.pred["identity_correspondence"]["prediction_to_reference"]["stone2"] = "stone2"
        b = evaluate_end(self.ref, self.pred)["boards"]["details"][0]
        self.assertFalse(b["correct"])
        self.assertEqual(b["identity_errors"], 1)
        self.assertEqual(b["matched_position_rmse"], 0)

    def test_abstained_identity_cannot_pass_board(self):
        self.pred["boards"][0]["stones"][0]["identity"] = None
        self.assertFalse(evaluate_end(self.ref, self.pred)["boards"]["details"][0]["correct"])

    def test_matching_track_id_without_reviewed_link_does_not_validate_identity(self):
        self.pred.pop("identity_correspondence")
        result = evaluate_end(self.ref, self.pred)
        self.assertEqual(result["cross_view_identity"]["assessed_predictions"], 0)
        self.assertEqual(result["cross_view_identity"]["coverage"], 0)
        self.assertEqual(result["boards"]["details"][0]["identity_abstentions"], 1)
        self.assertFalse(result["boards"]["details"][0]["correct"])

    def test_reviewed_mapping_allows_different_track_and_reference_ids(self):
        self.pred["events"][0]["arrival_identity"] = "local-7"
        self.pred["boards"][0]["stones"][0]["identity"] = "local-7"
        self.pred["identity_correspondence"]["prediction_to_reference"] = {
            "local-7": "stone1"
        }
        result = evaluate_end(self.ref, self.pred)
        self.assertEqual(result["cross_view_identity"]["correct"], 1)
        self.assertTrue(result["boards"]["details"][0]["correct"])

    def test_invalid_identity_mapping_rejected(self):
        self.pred["identity_correspondence"]["prediction_to_reference"] = {
            "local-1": "stone1", "local-2": "stone1"
        }
        with self.assertRaisesRegex(ValueError, "one-to-one"):
            evaluate_end(self.ref, self.pred)

    def test_unobservable_reference_not_assumed_correct(self):
        self.ref["boards"][0]["complete"] = False
        r = evaluate_end(self.ref, self.pred)["boards"]
        self.assertIsNone(r["complete_correct_fraction"])
        self.assertEqual(r["reference_incomplete"], 1)
        self.assertEqual(r["visible_stones"]["recall"], 1)
        self.assertIsNone(r["details"][0]["correct"])

    def test_incomplete_board_scores_only_observed_stones(self):
        self.ref["boards"][0]["complete"] = False
        self.ref["boards"][0]["stones"].append(
            dict(colour="yellow", position=[20, 20], identity=None)
        )
        self.pred["boards"][0]["stones"].append(
            dict(colour="yellow", position=[100, 100], identity=None)
        )
        b = evaluate_end(self.ref, self.pred)["boards"]
        detail = b["details"][0]
        self.assertEqual(b["visible_stones"], {
            "reference_count": 2, "matched": 1, "missed": 1, "recall": 0.5,
            "scope": "annotated_visible_stones_only; no precision or completeness claim for incomplete boards",
        })
        self.assertEqual(detail["matched_position_rmse"], 0)
        self.assertNotIn("extras", detail)
        self.assertIsNone(detail["correct"])

    def test_missing_prediction_misses_visible_stones_on_incomplete_board(self):
        self.ref["boards"][0]["complete"] = False
        self.pred["boards"] = []
        b = evaluate_end(self.ref, self.pred)["boards"]
        self.assertEqual(b["visible_stones"]["recall"], 0)
        self.assertEqual(b["details"][0]["visible_reference_misses"], 1)
        self.assertIsNone(b["complete_correct_fraction"])

    def test_position_outlier_is_miss_and_extra(self):
        self.pred["boards"][0]["stones"][0]["position"] = [100, 100]
        b = evaluate_end(self.ref, self.pred)["boards"]["details"][0]
        self.assertEqual((b["misses"], b["extras"]), (1, 1))
        self.assertIsNone(b["matched_position_rmse"])

    def test_known_complete_empty_board_is_valid(self):
        self.ref["boards"][0]["stones"] = []
        self.pred["boards"][0]["stones"] = []
        self.assertTrue(evaluate_end(self.ref, self.pred)["boards"]["details"][0]["correct"])

    def test_source_or_coordinate_mismatch_rejected(self):
        for key, value in [("source_sha256", "other"), ("source_interval_s", [0, 31])]:
            pred = copy.deepcopy(self.pred)
            pred[key] = value
            with self.assertRaises(ValueError):
                evaluate_end(self.ref, pred)
        self.pred["boards"][0]["coordinate_frame"] = "other_view"
        with self.assertRaises(ValueError):
            evaluate_end(self.ref, self.pred)

    def test_every_throw_needs_reference_board(self):
        self.ref["boards"] = []
        with self.assertRaises(ValueError):
            validate_reference(self.ref)

    def test_overlapping_delivery_intervals_rejected(self):
        self.ref["events"].append(dict(self.ref["events"][0], id="E02"))
        with self.assertRaises(ValueError):
            validate_reference(self.ref)

    def test_nonindependent_labels_rejected(self):
        self.ref["independent"] = False
        with self.assertRaises(ValueError):
            validate_reference(self.ref)

    def test_incomplete_end_review_cannot_claim_f1(self):
        self.ref["complete_end_reviewed"] = False
        with self.assertRaisesRegex(ValueError, "entire selected end"):
            evaluate_end(self.ref, self.pred)

    def test_wrong_timestamp_rejected(self):
        self.pred["boards"][0]["time_s"] = 21
        with self.assertRaises(ValueError):
            evaluate_end(self.ref, self.pred)

    def test_correct_outputs(self):
        r = evaluate_end(self.ref, self.pred)
        self.assertEqual((r["events"]["precision"], r["events"]["recall"],
                          r["events"]["f1"], r["events"]["colour_aware_f1"]),
                         (1, 1, 1, 1))
        self.assertEqual(r["boards"]["complete_correct_fraction"], 1)
        self.assertEqual(r["cross_view_identity"]["coverage"], 1)

    def test_practice_labels_rejected(self):
        self.ref["purpose"] = "practice_only"
        with self.assertRaises(ValueError):
            validate_reference(self.ref)

    def test_matching_maximizes_valid_pairs_before_distance(self):
        self.ref["boards"][0]["stones"] = [
            dict(colour="red", position=p, identity=None) for p in ([0, 0], [4, 0])
        ]
        self.pred["boards"][0]["stones"] = [
            dict(colour="red", position=p, identity=None) for p in ([0, 0], [0, 4])
        ]
        result = evaluate_end(self.ref, self.pred)["boards"]["details"][0]
        self.assertTrue(result["correct"])
        self.assertEqual(result["matched_position_errors"], [4, 4])


if __name__ == "__main__":
    unittest.main()
