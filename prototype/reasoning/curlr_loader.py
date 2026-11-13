"""CurlR official match dataset loader and preprocessor.

Loads the shot-level dataset from feasibility/sources/mxd_shots.rda (66,632 shots
across 804 international games), engineers game-state and board-state features,
and splits into train, validation, and held-out test partitions strictly by game
to prevent intra-game target leakage.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple
import numpy as np
import pandas as pd
import pyreadr

DEFAULT_RDA_PATH = Path(__file__).resolve().parents[2] / "feasibility" / "sources" / "mxd_shots.rda"

MACRO_FEATURE_NAMES = [
    "score_diff",
    "end",
    "shot",
    "has_hammer",
    "power_play",
]

BOARD_FEATURE_NAMES = [
    "house_diff",
    "button_diff",
    "four_ft_diff",
    "eight_ft_diff",
    "twelve_ft_diff",
    "guard_diff",
    "red_house",
    "yellow_house",
    "red_button",
    "yellow_button",
    "red_guards",
    "yellow_guards",
    "live_end_score_diff",
]

ALL_FEATURE_NAMES = MACRO_FEATURE_NAMES + BOARD_FEATURE_NAMES


def load_raw_curlr(rda_path: Path | str = DEFAULT_RDA_PATH) -> pd.DataFrame:
    """Load the raw mxd_shots data frame from the RDA file."""
    path = Path(rda_path)
    if not path.is_file():
        raise FileNotFoundError(f"CurlR data file not found: {path}")
    data = pyreadr.read_r(str(path))
    if "mxd_shots" not in data:
        key = list(data.keys())[0]
        return data[key]
    return data["mxd_shots"]


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer structured features and target variables from raw CurlR data."""
    out = df.copy()

    # Score differential from perspective of Team 1 (Red)
    t1_before = pd.to_numeric(out["T1Before"], errors="coerce").fillna(0.0)
    t2_before = pd.to_numeric(out["T2Before"], errors="coerce").fillna(0.0)
    out["score_diff"] = t1_before - t2_before
    out["end"] = pd.to_numeric(out["End"], errors="coerce").fillna(1.0)
    out["shot"] = pd.to_numeric(out["Shot"], errors="coerce").fillna(0.0)

    # Hammer possession: 1 if Team 1 (Red) has hammer, 0 if Team 2 (Yellow) has hammer
    out["has_hammer"] = (out["Hammer_End"] == out["T1"]).astype(int)

    # PowerPlay: 1 if active, 0 otherwise
    out["power_play"] = pd.to_numeric(out["PowerPlay"], errors="coerce").fillna(0.0).astype(int)

    # Zone counts and differences
    red_house = pd.to_numeric(out["Red_House"], errors="coerce").fillna(0.0)
    yellow_house = pd.to_numeric(out["Yellow_House"], errors="coerce").fillna(0.0)
    out["red_house"] = red_house
    out["yellow_house"] = yellow_house
    out["house_diff"] = red_house - yellow_house

    red_button = pd.to_numeric(out["Red_Button"], errors="coerce").fillna(0.0)
    yellow_button = pd.to_numeric(out["Yellow_Button"], errors="coerce").fillna(0.0)
    out["red_button"] = red_button
    out["yellow_button"] = yellow_button
    out["button_diff"] = red_button - yellow_button

    red_4ft = pd.to_numeric(out["Red_4FT"], errors="coerce").fillna(0.0)
    yellow_4ft = pd.to_numeric(out["Yellow_4FT"], errors="coerce").fillna(0.0)
    out["four_ft_diff"] = red_4ft - yellow_4ft

    red_8ft = pd.to_numeric(out["Red_8FT"], errors="coerce").fillna(0.0)
    yellow_8ft = pd.to_numeric(out["Yellow_8FT"], errors="coerce").fillna(0.0)
    out["eight_ft_diff"] = red_8ft - yellow_8ft

    red_12ft = pd.to_numeric(out["Red_12FT"], errors="coerce").fillna(0.0)
    yellow_12ft = pd.to_numeric(out["Yellow_12FT"], errors="coerce").fillna(0.0)
    out["twelve_ft_diff"] = red_12ft - yellow_12ft

    red_guards = (
        pd.to_numeric(out["Red_GL"], errors="coerce").fillna(0.0)
        + pd.to_numeric(out["Red_GC"], errors="coerce").fillna(0.0)
        + pd.to_numeric(out["Red_GR"], errors="coerce").fillna(0.0)
    )
    yellow_guards = (
        pd.to_numeric(out["Yellow_GL"], errors="coerce").fillna(0.0)
        + pd.to_numeric(out["Yellow_GC"], errors="coerce").fillna(0.0)
        + pd.to_numeric(out["Yellow_GR"], errors="coerce").fillna(0.0)
    )
    out["red_guards"] = red_guards
    out["yellow_guards"] = yellow_guards
    out["guard_diff"] = red_guards - yellow_guards

    red_score = pd.to_numeric(out["Red_Score"], errors="coerce").fillna(0.0)
    yellow_score = pd.to_numeric(out["Yellow_Score"], errors="coerce").fillna(0.0)
    out["live_end_score_diff"] = red_score - yellow_score

    # Targets
    final_t1 = pd.to_numeric(out["FinalT1"], errors="coerce").fillna(0.0)
    final_t2 = pd.to_numeric(out["FinalT2"], errors="coerce").fillna(0.0)
    out["t1_win"] = (final_t1 > final_t2).astype(int)

    # End score outcome: points scored in this end
    t1_after = pd.to_numeric(out["T1After"], errors="coerce")
    t2_after = pd.to_numeric(out["T2After"], errors="coerce")
    # For conceded ends ('X'), end score outcome is NaN
    out["end_points_t1"] = t1_after - t1_before
    out["end_points_t2"] = t2_after - t2_before
    out["end_points_diff"] = out["end_points_t1"] - out["end_points_t2"]

    # Composite game ID
    out["game_id"] = out["ID"].astype(str) + "::" + out["Game"].astype(str)

    return out


def split_by_game(
    df: pd.DataFrame,
    train_frac: float = 0.70,
    val_frac: float = 0.15,
    test_frac: float = 0.15,
    seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """Partition dataset into train, val, test subsets grouped by game_id.

    Ensures zero data leakage between splits: all shots from a given match
    belong exclusively to either train, val, or test.
    """
    total = train_frac + val_frac + test_frac
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"Fractions must sum to 1.0, got {total}")

    if "game_id" not in df.columns:
        df = prepare_features(df)

    unique_games = np.array(df["game_id"].unique())
    rng = np.random.RandomState(seed)
    shuffled = unique_games.copy()
    rng.shuffle(shuffled)

    n_total = len(shuffled)
    n_train = int(round(n_total * train_frac))
    n_val = int(round(n_total * val_frac))

    train_games = set(shuffled[:n_train])
    val_games = set(shuffled[n_train : n_train + n_val])
    test_games = set(shuffled[n_train + n_val :])

    train_df = df[df["game_id"].isin(train_games)].copy()
    val_df = df[df["game_id"].isin(val_games)].copy()
    test_df = df[df["game_id"].isin(test_games)].copy()

    metadata = {
        "seed": seed,
        "total_games": n_total,
        "train_games": len(train_games),
        "val_games": len(val_games),
        "test_games": len(test_games),
        "train_shots": len(train_df),
        "val_shots": len(val_df),
        "test_shots": len(test_df),
        "train_win_rate": float(train_df["t1_win"].mean()) if len(train_df) else 0.0,
        "test_win_rate": float(test_df["t1_win"].mean()) if len(test_df) else 0.0,
    }

    return train_df, val_df, test_df, metadata
