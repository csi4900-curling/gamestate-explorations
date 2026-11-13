"""Train a development cap-object verifier on one match and score another.

This is a patch identity diagnostic, not event detection or independent F1.
The threshold and classifier are fixed before evaluating the held-out match.
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


def make_features(manifest, labels):
    rows = []
    for source_id in labels:
        samples = [row for row in manifest["samples"] if row["source_id"] == source_id]
        video = ROOT / samples[0]["video"]
        if file_sha256(video) != samples[0]["video_sha256"]:
            raise ValueError(f"Source changed: {video}")
        capture = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
        fps = capture.get(cv2.CAP_PROP_FPS)
        counts = {}
        for sample in samples:
            track_id = sample["track_id"]
            index = counts.get(track_id, 0)
            counts[track_id] = index + 1
            label = labels[source_id][track_id][index]
            if label is None:
                continue
            capture.set(cv2.CAP_PROP_POS_FRAMES, round(sample["time_s"] * fps))
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Frame decode failed: {sample['id']}")
            image = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
            feature = patch_features(image, sample["crop_bbox"])
            rows.append(
                {
                    "id": sample["id"],
                    "source_id": source_id,
                    "track_id": track_id,
                    "time_s": sample["time_s"],
                    "label": label,
                    "feature": feature,
                }
            )
        capture.release()
    return rows


def counts(rows):
    tp = sum(row["label"] == 1 and row["predicted"] == 1 for row in rows)
    fp = sum(row["label"] == 0 and row["predicted"] == 1 for row in rows)
    fn = sum(row["label"] == 1 and row["predicted"] == 0 for row in rows)
    tn = sum(row["label"] == 0 and row["predicted"] == 0 for row in rows)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve the first cross-match result")
    manifest = json.loads((args.review / "manifest.json").read_text())
    labels = json.loads((args.review / "labels.json").read_text())
    rows = make_features(
        manifest,
        {key: value for key, value in labels.items() if key in ("china-dev", "slovakia-heldout")},
    )
    train = [row for row in rows if row["source_id"] == "china-dev"]
    holdout = [row for row in rows if row["source_id"] == "slovakia-heldout"]
    x_train = np.stack([row["feature"] for row in train])
    y_train = np.asarray([row["label"] for row in train])
    scaler = StandardScaler().fit(x_train)
    model = LinearSVC(C=0.1, class_weight="balanced", max_iter=5000, random_state=9031).fit(
        scaler.transform(x_train), y_train
    )
    x_holdout = np.stack([row["feature"] for row in holdout])
    scores = model.decision_function(scaler.transform(x_holdout))
    for row, score in zip(holdout, scores):
        row["score"] = float(score)
        row["predicted"] = int(score >= 0)
        del row["feature"]
    args.output.mkdir(parents=True)
    np.savez_compressed(
        args.output / "model.npz",
        mean=scaler.mean_,
        scale=scaler.scale_,
        weights=model.coef_,
        intercept=model.intercept_,
        threshold=np.asarray(0.0),
    )
    result = {
        "status": "development_cross_match_cap_patch_identity_probe",
        "train_source": "china-dev",
        "holdout_source": "slovakia-heldout",
        "review_manifest_sha256": file_sha256(args.review / "manifest.json"),
        "labels_sha256": file_sha256(args.review / "labels.json"),
        "runner_sha256": file_sha256(__file__),
        "model_sha256": file_sha256(args.output / "model.npz"),
        "training_count": {
            "positive": int(sum(y_train)),
            "negative": int(len(y_train) - sum(y_train)),
        },
        "threshold": 0,
        "holdout": counts(holdout),
        "holdout_rows": holdout,
        "limitations": [
            "Labels were authored by the model developer from three sampled frames per selected track; they are not independent ground truth.",
            "Tracks and frames were purposefully sampled, so this is not an unbiased object or event benchmark.",
            "Patch identity does not establish delivery, release, throw color, or end-to-end event precision/recall.",
        ],
    }
    (args.output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["holdout"], indent=2))


if __name__ == "__main__":
    main()
