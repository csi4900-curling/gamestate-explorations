"""Train on reviewed China cap tracks; score Estonia without refitting.

Development appearance probe only. Labels and selection are too small and
non-independent for an object or throw-event accuracy claim.
"""

import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from stone_patch_detector import patch_features


TRAIN_SOURCE = "Y_U6gzqORUs"
HOLDOUT_SOURCE = "PXGfMeiTKMA"


def load_rows(packet, manifest):
    rows = []
    for event in manifest["rows"]:
        if event["source_review"] not in ("real", "likely_false"):
            raise ValueError("Unexpected development review label")
        features = []
        for sample in event["samples"]:
            path = packet / sample["crop_path"]
            if file_sha256(path) != sample["crop_sha256"]:
                raise ValueError(f"Crop hash mismatch: {path}")
            image = cv2.imread(str(path))
            if image is None or image.shape[:2] != (48, 48):
                raise ValueError(f"Unreadable 48-pixel crop: {path}")
            features.append(patch_features(image, [0, 0, 48, 48]))
        if len(features) != manifest["samples_per_event"]:
            raise ValueError("Unexpected sample count")
        rows.append(
            {
                "source_id": event["source_id"],
                "event_id": event["event_id"],
                "review": event["source_review"],
                "label": int(event["source_review"] == "real"),
                "features": np.stack(features),
            }
        )
    return rows


def score_rows(rows, scaler, model):
    scored = []
    for row in rows:
        scores = model.decision_function(scaler.transform(row["features"]))
        mean_score = float(np.mean(scores))
        scored.append(
            {
                "source_id": row["source_id"],
                "event_id": row["event_id"],
                "source_review": row["review"],
                "sample_scores": [round(float(value), 6) for value in scores],
                "mean_score": round(mean_score, 6),
                "predicted_stone_like": bool(mean_score >= 0),
                "agrees_with_source_review": bool((mean_score >= 0) == bool(row["label"])),
            }
        )
    return scored


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output directory exists; preserve prior scores")
    manifest_path = args.packet / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    rows = load_rows(args.packet, manifest)
    train = [row for row in rows if row["source_id"] == TRAIN_SOURCE]
    holdout = [row for row in rows if row["source_id"] == HOLDOUT_SOURCE]
    if len(train) != 10 or len(holdout) != 8:
        raise ValueError("Unexpected frozen match split")
    x = np.concatenate([row["features"] for row in train])
    y = np.concatenate([np.repeat(row["label"], len(row["features"])) for row in train])
    scaler = StandardScaler().fit(x)
    model = LinearSVC(C=0.1, class_weight="balanced", max_iter=5000, random_state=9031).fit(
        scaler.transform(x), y
    )
    train_scored = score_rows(train, scaler, model)
    holdout_scored = score_rows(holdout, scaler, model)
    args.output.mkdir(parents=True)
    model_path = args.output / "model.npz"
    np.savez_compressed(
        model_path,
        mean=scaler.mean_,
        scale=scaler.scale_,
        weights=model.coef_,
        intercept=model.intercept_,
        threshold=np.asarray(0.0),
    )
    result = {
        "status": "development_frozen_cross_match_patch_probe",
        "packet_manifest_sha256": file_sha256(manifest_path),
        "feature_code_sha256": file_sha256(ROOT / "prototype/stone_patch_detector.py"),
        "runner_sha256": file_sha256(__file__),
        "model_sha256": file_sha256(model_path),
        "train_source": TRAIN_SOURCE,
        "holdout_source": HOLDOUT_SOURCE,
        "model": "standardized_patch_hog_hsv_linear_svm_C_0.1_balanced",
        "event_aggregation": "mean_of_three_sample_decision_scores",
        "threshold": 0.0,
        "training_events": len(train),
        "training_samples": len(x),
        "holdout_events": len(holdout),
        "holdout_agreements": sum(row["agrees_with_source_review"] for row in holdout_scored),
        "training_rows": train_scored,
        "holdout_rows": holdout_scored,
        "limitations": [
            "China and Estonia are same-production development recordings.",
            "Only two likely false China tracks and one likely false Estonia track were reviewed.",
            "The development labels are same-agent source judgments, not independent ground truth.",
            "A patch score does not prove the object was newly delivered or that a full video was segmented correctly.",
        ],
    }
    (args.output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {"holdout_agreements": result["holdout_agreements"], "holdout_events": len(holdout)}
        )
    )


if __name__ == "__main__":
    main()
