import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from box_evaluation import iou, score_boxes


class BoxEvaluationTests(unittest.TestCase):
    def test_overlap(self):
        self.assertEqual(iou([0, 0, 10, 10], [0, 0, 10, 10]), 1)
        self.assertEqual(iou([0, 0, 10, 10], [20, 20, 10, 10]), 0)
        self.assertAlmostEqual(iou([0, 0, 10, 10], [5, 0, 10, 10]), 1 / 3)

    def test_duplicate_prediction_is_extra(self):
        r = {"colour": "red", "bbox": [1, 2, 3, 4]}
        result = score_boxes([r], [r, r])
        self.assertEqual((result["matches"], result["extras"]), (1, 1))

    def test_colour_error_misses_reference(self):
        r = {"colour": "red", "bbox": [1, 2, 3, 4]}
        result = score_boxes([r], [dict(r, colour="yellow")])
        self.assertEqual((result["matches"], result["misses"], result["extras"]), (0, 1, 1))

    def test_empty_predictions(self):
        result = score_boxes([{"colour": "red", "bbox": [1, 2, 3, 4]}], [])
        self.assertEqual(result["misses"], 1)


if __name__ == "__main__":
    unittest.main()
