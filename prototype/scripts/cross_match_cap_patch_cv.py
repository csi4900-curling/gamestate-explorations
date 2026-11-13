"""Leave-one-match-out diagnostic for the research cap-patch classifier.

The three source matches are exposed development footage. No fold is an
independent event benchmark, but this catches one-match appearance overfit.
"""

import argparse
import json
from pathlib import Path
import sys

import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from scripts.score_cap_patch_transfer import counts, make_features


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviews", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first cross-match score")
    rows = []
    inputs = []
    for review in args.reviews:
        manifest_path, labels_path = review / "manifest.json", review / "labels.json"
        manifest = json.loads(manifest_path.read_text())
        labels = json.loads(labels_path.read_text())
        sources = {key: value for key, value in labels.items() if isinstance(value, dict)}
        rows.extend(make_features(manifest, sources))
        inputs.append(
            {
                "review": str(review),
                "manifest_sha256": file_sha256(manifest_path),
                "labels_sha256": file_sha256(labels_path),
            }
        )
    source_ids = sorted({row["source_id"] for row in rows})
    if len(source_ids) != 3:
        parser.error("Three distinct source matches required")
    args.output.mkdir(parents=True)
    folds = []
    for heldout in source_ids:
        fit = [row for row in rows if row["source_id"] != heldout]
        test = [row for row in rows if row["source_id"] == heldout]
        x_fit = np.stack([row["feature"] for row in fit])
        y_fit = np.asarray([row["label"] for row in fit])
        scaler = StandardScaler().fit(x_fit)
        model = LinearSVC(C=0.1, class_weight="balanced", max_iter=5000, random_state=9031).fit(
            scaler.transform(x_fit), y_fit
        )
        x_test = np.stack([row["feature"] for row in test])
        scores = model.decision_function(scaler.transform(x_test))
        evaluated = [
            {
                "id": row["id"],
                "track_id": row["track_id"],
                "label": row["label"],
                "score": float(score),
                "predicted": int(score >= 0),
            }
            for row, score in zip(test, scores)
        ]
        model_path = args.output / f"model-excluding-{heldout}.npz"
        np.savez_compressed(
            model_path,
            mean=scaler.mean_,
            scale=scaler.scale_,
            weights=model.coef_,
            intercept=model.intercept_,
            threshold=np.asarray(0.0),
        )
        folds.append(
            {
                "heldout": heldout,
                "train_sources": [source for source in source_ids if source != heldout],
                "train_count": len(fit),
                "test_count": len(test),
                "model_sha256": file_sha256(model_path),
                "score": counts(evaluated),
                "rows": evaluated,
            }
        )
    total = counts([row for fold in folds for row in fold["rows"]])
    result = {
        "status": "development_leave_one_match_out_cap_patch_identity_probe",
        "inputs": inputs,
        "runner_sha256": file_sha256(__file__),
        "model_specification": "HOG+HSV on 3x cap context; StandardScaler; balanced LinearSVC C=0.1; threshold=0; no fold-specific tuning",
        "folds": folds,
        "pooled": total,
        "limitations": [
            "All source matches and labels are exposed development material.",
            "Three handpicked samples per track do not represent detection proposals or full broadcasts.",
            "Patch identity is not delivered-stone identity or throw-event F1.",
        ],
    }
    (args.output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({fold["heldout"]: fold["score"] for fold in folds}, indent=2))


if __name__ == "__main__":
    main()
