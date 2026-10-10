"""Leave-one-match-out developmental delivery-origin shot classification."""

import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from shot_origin_model import shot_features


def score(rows):
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
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first cross-match score")
    labels = json.loads(args.labels.read_text())
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    rows = []
    reviews = []
    for source, spec in labels["sources"].items():
        review = ROOT / spec["review"]
        manifest_path = review / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        video = (
            ROOT
            / {
                "china-dev": "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4",
                "slovakia-dev": "validation/throw-event-benchmark/paralympics-2022-slovakia-usa/source.mp4",
                "swiss-dev": "validation/throw-event-benchmark/paralympics-2022-sweden-switzerland/source.mp4",
            }[source]
        )
        digest = file_sha256(video)
        if digest != manifest["source_sha256"] or digest == reserved["source_sha256"]:
            raise ValueError(f"Invalid development source: {source}")
        if set(spec["labels"]) != {shot["id"] for shot in manifest["shots"]}:
            raise ValueError(f"Shot labels incomplete: {source}")
        capture = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
        fps = capture.get(cv2.CAP_PROP_FPS)
        for shot in manifest["shots"]:
            frames = []
            for t in shot["frame_times_s"]:
                capture.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError(f"Frame decode failed: {source} {t}")
                frames.append(frame)
            rows.append(
                {
                    "source": source,
                    "shot_id": shot["id"],
                    "interval_s": shot["interval_s"],
                    "label": spec["labels"][shot["id"]],
                    "feature": shot_features(frames),
                }
            )
        capture.release()
        reviews.append(
            {
                "source": source,
                "manifest_sha256": file_sha256(manifest_path),
                "video_sha256": digest,
            }
        )
    if any(row["label"] not in (0, 1) for row in rows):
        parser.error("This probe requires resolved binary development labels")
    args.output.mkdir(parents=True)
    folds = []
    for heldout in labels["sources"]:
        fit = [row for row in rows if row["source"] != heldout]
        test = [row for row in rows if row["source"] == heldout]
        x_fit = np.stack([row["feature"] for row in fit])
        y_fit = np.asarray([row["label"] for row in fit])
        scaler = StandardScaler().fit(x_fit)
        model = LogisticRegression(
            C=0.05, class_weight="balanced", max_iter=5000, random_state=9031
        ).fit(scaler.transform(x_fit), y_fit)
        probabilities = model.predict_proba(
            scaler.transform(np.stack([row["feature"] for row in test]))
        )[:, 1]
        evaluated = [
            {
                "source": heldout,
                "shot_id": row["shot_id"],
                "interval_s": row["interval_s"],
                "label": row["label"],
                "probability": float(p),
                "predicted": int(p >= 0.5),
            }
            for row, p in zip(test, probabilities)
        ]
        model_path = args.output / f"model-excluding-{heldout}.npz"
        np.savez_compressed(
            model_path,
            mean=scaler.mean_,
            scale=scaler.scale_,
            weights=model.coef_,
            intercept=model.intercept_,
        )
        folds.append(
            {
                "heldout": heldout,
                "train_sources": [s for s in labels["sources"] if s != heldout],
                "model_sha256": file_sha256(model_path),
                "score": score(evaluated),
                "rows": evaluated,
            }
        )
    result = {
        "status": "retrospective_development_shot_origin_transfer_probe",
        "labels_sha256": file_sha256(args.labels),
        "reviews": reviews,
        "feature_code_sha256": file_sha256(ROOT / "prototype/shot_origin_model.py"),
        "runner_sha256": file_sha256(__file__),
        "model_specification": "Three-frame spatial ice/color/edge grid plus live overlay; balanced logistic regression C=0.05; threshold=0.5; no fold-specific tuning",
        "folds": folds,
        "pooled": score([row for fold in folds for row in fold["rows"]]),
        "limitations": [
            "Shot labels are retrospective agent review of exposed footage, not independent event labels.",
            "Only 58 shots from one broadcaster and three matches; complete-video reliability is unknown.",
            "A throwing-side camera view does not by itself prove an actual release or stone identity.",
        ],
    }
    (args.output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({fold["heldout"]: fold["score"] for fold in folds}, indent=2))


if __name__ == "__main__":
    main()
