"""Unit tests for win probability model and reasoning layer."""

import unittest
import numpy as np
import pandas as pd

from prototype.reasoning.curlr_loader import prepare_features
from prototype.reasoning.win_probability_model import (
    EmpiricalWinProbabilityTable,
    CalibratedWinProbabilityModel,
    ExpectedScoreModel,
    compute_ece,
)


class TestWinProbabilityModel(unittest.TestCase):
    def setUp(self):
        # Synthetic dataset with 30 shots
        n = 30
        self.df = pd.DataFrame(
            {
                "ID": ["WMDCC2024"] * n,
                "Game": ["G01"] * (n // 2) + ["G02"] * (n - n // 2),
                "T1": ["CAN-Canada"] * n,
                "T2": ["SWE-Sweden"] * n,
                "Hammer_End": ["CAN-Canada" if i % 2 == 0 else "SWE-Sweden" for i in range(n)],
                "End": [(i % 8) + 1 for i in range(n)],
                "Shot": [(i % 10) + 1 for i in range(n)],
                "T1Before": [float(i % 5) for i in range(n)],
                "T2Before": [float((i + 1) % 5) for i in range(n)],
                "T1After": [str((i % 5) + 1) for i in range(n)],
                "T2After": [str((i + 1) % 5) for i in range(n)],
                "FinalT1": [7.0 if i < (n // 2) else 3.0 for i in range(n)],
                "FinalT2": [4.0 if i < (n // 2) else 6.0 for i in range(n)],
                "PowerPlay": [0.0] * n,
                "Red_House": [float(i % 3) for i in range(n)],
                "Yellow_House": [float((i + 1) % 3) for i in range(n)],
                "Red_Button": [0.0] * n,
                "Yellow_Button": [0.0] * n,
                "Red_4FT": [0.0] * n,
                "Yellow_4FT": [0.0] * n,
                "Red_8FT": [float(i % 2) for i in range(n)],
                "Yellow_8FT": [float((i + 1) % 2) for i in range(n)],
                "Red_12FT": [0.0] * n,
                "Yellow_12FT": [0.0] * n,
                "Red_GL": [0.0] * n,
                "Yellow_GL": [0.0] * n,
                "Red_GC": [0.0] * n,
                "Yellow_GC": [0.0] * n,
                "Red_GR": [0.0] * n,
                "Yellow_GR": [0.0] * n,
                "Red_Score": [1.0] * n,
                "Yellow_Score": [0.0] * n,
            }
        )
        self.prep = prepare_features(self.df)

    def test_compute_ece(self):
        y_true = np.array([1, 1, 0, 0])
        y_prob = np.array([0.9, 0.8, 0.2, 0.1])
        ece = compute_ece(y_true, y_prob, n_bins=5)
        self.assertGreaterEqual(ece, 0.0)
        self.assertLessEqual(ece, 1.0)

    def test_empirical_table_fit_and_predict(self):
        table = EmpiricalWinProbabilityTable(alpha=1.0)
        table.fit(self.prep)
        probs = table.predict_proba(self.prep)
        self.assertEqual(len(probs), len(self.prep))
        self.assertTrue(np.all((probs >= 0.0) & (probs <= 1.0)))

    def test_calibrated_ml_model_fit_and_predict(self):
        model = CalibratedWinProbabilityModel(cv=2, random_state=42)
        model.fit(self.prep)
        probs = model.predict_proba(self.prep)
        self.assertEqual(len(probs), len(self.prep))
        self.assertTrue(np.all((probs >= 0.0) & (probs <= 1.0)))

        metrics = model.evaluate(self.prep)
        self.assertIn("brier_score", metrics)
        self.assertIn("log_loss", metrics)
        self.assertIn("roc_auc", metrics)
        self.assertIn("ece", metrics)
        self.assertLess(metrics["brier_score"], 0.5)

    def test_expected_score_model(self):
        es = ExpectedScoreModel(random_state=42)
        es.fit(self.prep)
        preds = es.predict(self.prep)
        self.assertEqual(len(preds), len(self.prep))
        eval_res = es.evaluate(self.prep)
        self.assertIn("mae", eval_res)
        self.assertIn("rmse", eval_res)


if __name__ == "__main__":
    unittest.main()
