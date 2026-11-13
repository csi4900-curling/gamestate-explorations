"""Unit tests for CurlR data loader and preprocessor."""

from pathlib import Path
import unittest
import pandas as pd

from prototype.reasoning.curlr_loader import (
    DEFAULT_RDA_PATH,
    ALL_FEATURE_NAMES,
    prepare_features,
    split_by_game,
)


class TestCurlRLoader(unittest.TestCase):
    def setUp(self):
        # Create a synthetic dataframe matching the CurlR schema
        self.sample_df = pd.DataFrame(
            {
                "ID": ["WMDCC2024", "WMDCC2024", "WMDCC2024", "WMDCC2024", "OWG2022", "OWG2022"],
                "Game": ["G01", "G01", "G01", "G01", "G02", "G02"],
                "T1": ["CAN-Canada"] * 6,
                "T2": ["SWE-Sweden"] * 6,
                "Hammer_End": [
                    "CAN-Canada",
                    "CAN-Canada",
                    "SWE-Sweden",
                    "SWE-Sweden",
                    "CAN-Canada",
                    "SWE-Sweden",
                ],
                "End": [1, 1, 2, 2, 1, 1],
                "Shot": [1, 2, 1, 2, 1, 2],
                "T1Before": [0, 0, 1, 1, 0, 0],
                "T2Before": [0, 0, 0, 0, 0, 0],
                "T1After": ["1", "1", "2", "2", "0", "0"],
                "T2After": ["0", "0", "1", "1", "1", "1"],
                "FinalT1": [7, 7, 7, 7, 4, 4],
                "FinalT2": [5, 5, 5, 5, 6, 6],
                "PowerPlay": [0, 0, 1, 1, 0, 0],
                "Red_House": [1, 2, 1, 1, 0, 1],
                "Yellow_House": [0, 1, 1, 2, 1, 0],
                "Red_Button": [1, 1, 0, 0, 0, 0],
                "Yellow_Button": [0, 0, 0, 0, 0, 0],
                "Red_4FT": [1, 1, 0, 0, 0, 0],
                "Yellow_4FT": [0, 0, 1, 1, 0, 0],
                "Red_8FT": [0, 1, 1, 1, 0, 1],
                "Yellow_8FT": [0, 1, 0, 1, 1, 0],
                "Red_12FT": [0, 0, 0, 0, 0, 0],
                "Yellow_12FT": [0, 0, 0, 0, 0, 0],
                "Red_GL": [0, 0, 1, 1, 0, 0],
                "Yellow_GL": [0, 0, 0, 0, 0, 0],
                "Red_GC": [1, 1, 0, 0, 1, 1],
                "Yellow_GC": [0, 0, 1, 1, 0, 0],
                "Red_GR": [0, 0, 0, 0, 0, 0],
                "Yellow_GR": [0, 0, 0, 0, 0, 0],
                "Red_Score": [1, 1, 0, 0, 0, 1],
                "Yellow_Score": [0, 0, 1, 1, 1, 0],
            }
        )

    def test_feature_engineering_columns(self):
        prep = prepare_features(self.sample_df)
        for col in ALL_FEATURE_NAMES:
            self.assertIn(col, prep.columns, f"Missing feature {col}")

        # Check score_diff
        self.assertEqual(prep["score_diff"].iloc[0], 0.0)
        self.assertEqual(prep["score_diff"].iloc[2], 1.0)

        # Check hammer
        self.assertEqual(prep["has_hammer"].iloc[0], 1)
        self.assertEqual(prep["has_hammer"].iloc[2], 0)

        # Check target
        self.assertEqual(prep["t1_win"].iloc[0], 1)
        self.assertEqual(prep["t1_win"].iloc[4], 0)

    def test_split_by_game_isolation(self):
        prep = prepare_features(self.sample_df)
        train, val, test, meta = split_by_game(
            prep, train_frac=0.5, val_frac=0.0, test_frac=0.5, seed=42
        )

        self.assertEqual(meta["total_games"], 2)
        # Ensure games don't overlap across splits
        train_games = set(train["game_id"])
        test_games = set(test["game_id"])
        self.assertTrue(train_games.isdisjoint(test_games))
        self.assertEqual(len(train) + len(test), len(prep))

    def test_default_file_exists(self):
        self.assertTrue(Path(DEFAULT_RDA_PATH).is_file())


if __name__ == "__main__":
    unittest.main()
