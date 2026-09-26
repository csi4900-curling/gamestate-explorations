import unittest, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from stone_accuracy import match_observations, position_statistics


class StoneAccuracyTests(unittest.TestCase):
    def test_metric_error_does_not_change_image_match(self):
        pred = [{"colour": "red", "pixel_center": [100, 100], "diagram_metric_m": [100, 100]}]
        refs = [
            {"colour": "red", "pixel": [101, 100], "matching_radius_px": 10, "reference_m": [0, 0]}
        ]
        pairs, fp, fn = match_observations(pred, refs)
        self.assertEqual(pairs, [(0, 0)])
        self.assertEqual(fp, [])
        self.assertEqual(fn, [])

    def test_two_predictions_cannot_claim_one_reference(self):
        pred = [{"colour": "red", "pixel_center": [i, 0]} for i in [0, 1]]
        ref = [{"colour": "red", "pixel": [0, 0], "matching_radius_px": 10}]
        pairs, fp, fn = match_observations(pred, ref)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(len(fp), 1)
        self.assertEqual(fn, [])

    def test_matching_maximizes_valid_pairs_in_crowded_case(self):
        pred = [{"colour": "red", "pixel_center": [x, 0]} for x in [0, 9]]
        refs = [
            {"colour": "red", "pixel": [x, 0], "matching_radius_px": r}
            for x, r in [(0, 10), (-1, 2)]
        ]
        pairs, fp, fn = match_observations(pred, refs)
        self.assertEqual(len(pairs), 2)
        self.assertEqual(fp, [])
        self.assertEqual(fn, [])

    def test_colour_and_distance_gates_keep_misses(self):
        p = [
            {"colour": "red", "pixel_center": [0, 0]},
            {"colour": "yellow", "pixel_center": [50, 50]},
        ]
        r = [{"colour": "yellow", "pixel": [0, 0], "matching_radius_px": 10}]
        pairs, fp, fn = match_observations(p, r)
        self.assertEqual(pairs, [])
        self.assertEqual(len(fp), 2)
        self.assertEqual(fn, [0])

    def test_no_matches_means_unknown_error_not_zero(self):
        self.assertEqual(position_statistics([])["n"], 0)
        self.assertIsNone(position_statistics([])["rmse_cm"])

    def test_large_errors_are_preserved(self):
        r = position_statistics([3, 4, 100])
        self.assertEqual(r["max_cm"], 100)
        self.assertGreater(r["rmse_cm"], 57)


if __name__ == "__main__":
    unittest.main()
