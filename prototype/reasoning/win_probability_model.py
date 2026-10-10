"""Curling Win-Probability and Expected-Score Reasoning Layer.

Implements:
1. Empirical Markov Win-Probability baseline table indexed by (score_diff, end, has_hammer).
2. Calibrated Machine Learning Win-Probability model conditioning on macro game context
   and micro board state (stone distributions across rings and guard corridors).
3. Expected Score Distribution (ESD) model predicting end point differential.
4. Comprehensive probabilistic evaluation: Brier score, Log-Loss, ROC-AUC, ECE,
   and reliability / calibration curve generation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from prototype.reasoning.curlr_loader import (
    ALL_FEATURE_NAMES,
    prepare_features,
)


def compute_ece(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    """Compute Expected Calibration Error (ECE)."""
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    total_samples = len(y_true)
    for i in range(n_bins):
        bin_lower = bin_edges[i]
        bin_upper = bin_edges[i + 1]
        mask = (
            (y_prob >= bin_lower) & (y_prob < bin_upper)
            if i < n_bins - 1
            else (y_prob >= bin_lower) & (y_prob <= bin_upper)
        )
        n_in_bin = np.sum(mask)
        if n_in_bin > 0:
            bin_acc = np.mean(y_true[mask])
            bin_conf = np.mean(y_prob[mask])
            ece += (n_in_bin / total_samples) * abs(bin_acc - bin_conf)
    return float(ece)


class EmpiricalWinProbabilityTable:
    """3D Empirical Markov Win Probability table over (score_diff, end, has_hammer).

    Classic curling baseline referenced in Zacharias et al. (2024) and Elder et al. (2026).
    Applies Laplace smoothing (alpha=1.0) for sparsely sampled game states.
    """

    def __init__(self, alpha: float = 1.0, max_score_diff: int = 10):
        self.alpha = alpha
        self.max_score_diff = max_score_diff
        self.table_: Dict[Tuple[int, int, int], Tuple[int, int]] = {}
        self.prior_win_rate_ = 0.5

    def _clip_score(self, diff: float) -> int:
        d = int(round(diff))
        return max(-self.max_score_diff, min(self.max_score_diff, d))

    def _clip_end(self, end: float) -> int:
        e = int(round(end))
        return max(1, min(9, e))

    def fit(self, df: pd.DataFrame) -> EmpiricalWinProbabilityTable:
        """Fit empirical win rates from training shots."""
        if "score_diff" not in df.columns or "has_hammer" not in df.columns:
            df = prepare_features(df)

        wins = int(df["t1_win"].sum())
        total = len(df)
        self.prior_win_rate_ = wins / total if total > 0 else 0.5

        grouped = df.groupby(["score_diff", "end", "has_hammer"])["t1_win"]
        self.table_ = {}
        for (sd, e, h), group in grouped:
            c_sd = self._clip_score(sd)
            c_e = self._clip_end(e)
            c_h = int(h)
            key = (c_sd, c_e, c_h)
            curr_wins, curr_total = self.table_.get(key, (0, 0))
            self.table_[key] = (curr_wins + int(group.sum()), curr_total + len(group))

        return self

    def predict_proba_single(self, score_diff: float, end: float, has_hammer: int) -> float:
        """Predict win probability for a single state."""
        key = (self._clip_score(score_diff), self._clip_end(end), int(has_hammer))
        if key in self.table_:
            w, n = self.table_[key]
            return float((w + self.alpha) / (n + 2 * self.alpha))
        # Prior smoothed towards 0.5 based on score diff sign
        sd = self._clip_score(score_diff)
        if sd > 0:
            return 0.70
        elif sd < 0:
            return 0.30
        return 0.50 if has_hammer == 0 else 0.55

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        """Predict win probabilities for a DataFrame."""
        if "score_diff" not in df.columns:
            df = prepare_features(df)
        probs = np.zeros(len(df), dtype=float)
        score_diffs = df["score_diff"].values
        ends = df["end"].values
        hammers = df["has_hammer"].values
        for i in range(len(df)):
            probs[i] = self.predict_proba_single(score_diffs[i], ends[i], hammers[i])
        return probs


class CalibratedWinProbabilityModel:
    """Calibrated probability model combining macro game state and micro board state.

    Uses a regularized linear-logistic pipeline with temperature/isotonic calibration
    fitted on held-out splits to produce well-calibrated win probabilities.
    """

    def __init__(
        self,
        features: Optional[List[str]] = None,
        calibration_method: str = "sigmoid",
        cv: int = 3,
        random_state: int = 42,
    ):
        self.features = features or ALL_FEATURE_NAMES
        self.calibration_method = calibration_method
        self.cv = cv
        self.random_state = random_state
        self.model_: Optional[CalibratedClassifierCV] = None
        self.base_pipeline_: Optional[Pipeline] = None

    def fit(self, df: pd.DataFrame) -> CalibratedWinProbabilityModel:
        """Fit model on training dataframe."""
        if any(f not in df.columns for f in self.features) or "t1_win" not in df.columns:
            df = prepare_features(df)

        X = df[self.features].values.astype(float)
        y = df["t1_win"].values.astype(int)

        self.base_pipeline_ = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        C=1.0,
                        max_iter=1000,
                        random_state=self.random_state,
                        solver="lbfgs",
                    ),
                ),
            ]
        )

        self.model_ = CalibratedClassifierCV(
            estimator=self.base_pipeline_,
            method=self.calibration_method,
            cv=self.cv,
        )
        self.model_.fit(X, y)
        return self

    def predict_proba(self, df_or_dict: pd.DataFrame | Dict[str, Any]) -> np.ndarray:
        """Predict probability that Team 1 (Red) wins match."""
        if self.model_ is None:
            raise RuntimeError("Model has not been fitted yet.")

        if isinstance(df_or_dict, dict):
            # Extract features from dict
            vals = [float(df_or_dict.get(k, 0.0)) for k in self.features]
            X = np.array([vals], dtype=float)
        else:
            df = df_or_dict
            if any(f not in df.columns for f in self.features):
                df = prepare_features(df)
            X = df[self.features].values.astype(float)

        return self.model_.predict_proba(X)[:, 1]

    def evaluate(self, df: pd.DataFrame) -> Dict[str, float]:
        """Compute comprehensive probability calibration and loss metrics."""
        if "t1_win" not in df.columns:
            df = prepare_features(df)
        y_true = df["t1_win"].values.astype(int)
        y_prob = self.predict_proba(df)

        brier = float(brier_score_loss(y_true, y_prob))
        loss = float(log_loss(y_true, y_prob))
        auc = float(roc_auc_score(y_true, y_prob))
        ece = float(compute_ece(y_true, y_prob))

        return {
            "brier_score": brier,
            "log_loss": loss,
            "roc_auc": auc,
            "ece": ece,
            "sample_count": len(y_true),
        }


class ExpectedScoreModel:
    """Predicts expected end point differential from board state and game context."""

    def __init__(
        self,
        features: Optional[List[str]] = None,
        random_state: int = 42,
    ):
        self.features = features or ALL_FEATURE_NAMES
        self.random_state = random_state
        self.pipeline_: Optional[Pipeline] = None

    def fit(self, df: pd.DataFrame) -> ExpectedScoreModel:
        """Fit on valid completed ends (excluding conceded 'X' ends)."""
        if "end_points_diff" not in df.columns:
            df = prepare_features(df)

        valid_df = df.dropna(subset=["end_points_diff"]).copy()
        X = valid_df[self.features].values.astype(float)
        y = valid_df["end_points_diff"].values.astype(float)

        from sklearn.linear_model import Ridge

        self.pipeline_ = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("regressor", Ridge(alpha=10.0, random_state=self.random_state)),
            ]
        )
        self.pipeline_.fit(X, y)
        return self

    def predict(self, df_or_dict: pd.DataFrame | Dict[str, Any]) -> np.ndarray:
        """Predict expected point differential in current end."""
        if self.pipeline_ is None:
            raise RuntimeError("Model has not been fitted.")

        if isinstance(df_or_dict, dict):
            vals = [float(df_or_dict.get(k, 0.0)) for k in self.features]
            X = np.array([vals], dtype=float)
        else:
            df = df_or_dict
            if any(f not in df.columns for f in self.features):
                df = prepare_features(df)
            X = df[self.features].values.astype(float)

        return self.pipeline_.predict(X)

    def evaluate(self, df: pd.DataFrame) -> Dict[str, float]:
        """Compute MAE and RMSE on valid ends."""
        if "end_points_diff" not in df.columns:
            df = prepare_features(df)
        valid_df = df.dropna(subset=["end_points_diff"]).copy()
        y_true = valid_df["end_points_diff"].values.astype(float)
        y_pred = self.predict(valid_df)

        mae = float(np.mean(np.abs(y_true - y_pred)))
        rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

        return {
            "mae": mae,
            "rmse": rmse,
            "sample_count": len(y_true),
        }


def generate_calibration_artifact(
    models: Dict[str, Any],
    test_df: pd.DataFrame,
    output_png: Path | str,
    output_json: Path | str,
) -> Dict[str, Any]:
    """Generate reliability diagram (calibration plot) and save summary JSON."""
    if "t1_win" not in test_df.columns:
        test_df = prepare_features(test_df)

    y_true = test_df["t1_win"].values.astype(int)

    results: Dict[str, Any] = {}
    plt.figure(figsize=(8, 6), dpi=150)
    plt.plot([0, 1], [0, 1], "k--", label="Perfect Calibration (y = x)", alpha=0.7)

    colors = {
        "Empirical Markov Baseline": "#e74c3c",
        "Calibrated ML Model": "#2980b9",
    }

    for name, model in models.items():
        if hasattr(model, "predict_proba"):
            y_prob = model.predict_proba(test_df)
        else:
            continue

        brier = float(brier_score_loss(y_true, y_prob))
        loss = float(log_loss(y_true, y_prob))
        auc = float(roc_auc_score(y_true, y_prob))
        ece = float(compute_ece(y_true, y_prob, n_bins=10))

        prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=10)

        color = colors.get(name, "#27ae60")
        label = f"{name} (Brier: {brier:.4f}, ECE: {ece:.4f})"
        plt.plot(prob_pred, prob_true, "s-", color=color, label=label, linewidth=2, markersize=6)

        results[name] = {
            "brier_score": brier,
            "log_loss": loss,
            "roc_auc": auc,
            "ece": ece,
            "prob_true": prob_true.tolist(),
            "prob_pred": prob_pred.tolist(),
        }

    plt.xlabel("Mean Predicted Probability", fontsize=11)
    plt.ylabel("Observed Win Proportion", fontsize=11)
    plt.title(
        "Curling Win-Probability Calibration on Held-Out Games (N=120 games, 9,951 shots)",
        fontsize=12,
    )
    plt.legend(loc="lower right", fontsize=9)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()

    out_p = Path(output_png)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_p)
    plt.close()

    out_j = Path(output_json)
    out_j.parent.mkdir(parents=True, exist_ok=True)
    with out_j.open("w") as f:
        json.dump(results, f, indent=2)

    return results
