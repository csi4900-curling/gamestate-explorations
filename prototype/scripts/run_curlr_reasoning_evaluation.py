"""Execute Step 14 Reasoning Layer Evaluation on CurlR Dataset.

Fits empirical baseline and calibrated probability models on the 70% training split,
evaluates on the 15% held-out test split (120 games, 9,951 shots), and produces
the official calibration plot and summary JSON artifacts.
"""

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from prototype.reasoning.curlr_loader import load_raw_curlr, prepare_features, split_by_game
from prototype.reasoning.win_probability_model import (
    EmpiricalWinProbabilityTable,
    CalibratedWinProbabilityModel,
    ExpectedScoreModel,
    generate_calibration_artifact,
)

ARTIFACTS_DIR = ROOT / "artifacts" / "reasoning"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("[1/5] Loading CurlR official match records (mxd_shots.rda)...")
    raw = load_raw_curlr()
    df = prepare_features(raw)
    train_df, val_df, test_df, meta = split_by_game(
        df, train_frac=0.70, val_frac=0.15, test_frac=0.15, seed=42
    )
    print(
        f"       Partitioned {meta['total_games']} games -> train: {meta['train_games']}, val: {meta['val_games']}, test: {meta['test_games']}"
    )
    print(
        f"       Shots -> train: {meta['train_shots']}, val: {meta['val_shots']}, test: {meta['test_shots']}"
    )

    print("[2/5] Fitting Empirical Markov Win-Probability Baseline...")
    markov = EmpiricalWinProbabilityTable(alpha=1.0)
    markov.fit(train_df)

    print("[3/5] Fitting Calibrated ML Win-Probability Model...")
    ml_model = CalibratedWinProbabilityModel(calibration_method="sigmoid", cv=3, random_state=42)
    ml_model.fit(train_df)
    ml_eval = ml_model.evaluate(test_df)
    print(
        f"       ML Model Test Eval -> Brier: {ml_eval['brier_score']:.4f}, Log-Loss: {ml_eval['log_loss']:.4f}, AUC: {ml_eval['roc_auc']:.4f}, ECE: {ml_eval['ece']:.4f}"
    )

    print("[4/5] Fitting Expected Score Model...")
    es_model = ExpectedScoreModel(random_state=42)
    es_model.fit(train_df)
    es_eval = es_model.evaluate(test_df)
    print(
        f"       Expected Score Test Eval -> MAE: {es_eval['mae']:.4f}, RMSE: {es_eval['rmse']:.4f}"
    )

    print("[5/5] Generating Calibration Curves & Summary Artifacts...")
    png_path = ARTIFACTS_DIR / "curlr_win_probability_calibration.png"
    json_path = ARTIFACTS_DIR / "curlr_reasoning_metrics.json"

    models = {
        "Empirical Markov Baseline": markov,
        "Calibrated ML Model": ml_model,
    }
    cal_results = generate_calibration_artifact(models, test_df, png_path, json_path)

    summary = {
        "dataset_metadata": meta,
        "win_probability_metrics": cal_results,
        "expected_score_metrics": es_eval,
        "calibration_plot": str(png_path.relative_to(ROOT)),
    }
    with (ARTIFACTS_DIR / "step14_reasoning_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)

    print("\nSUCCESS: Reasoning layer evaluated.")
    print(f"         Calibration Plot: {png_path}")
    print(f"         Metrics Summary:  {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
