"""Postscore development probe: delivery shot plus following shot and live phase."""

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
from learned_gap_confirmation import compact_overlay_visible
from scripts.score_shot_origin_transfer import score
from shot_origin_model import shot_features

VIDEOS = {
    "china-dev": "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4",
    "slovakia-dev": "validation/throw-event-benchmark/paralympics-2022-slovakia-usa/source.mp4",
    "swiss-dev": "validation/throw-event-benchmark/paralympics-2022-sweden-switzerland/source.mp4",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first postscore pairing result")
    labels = json.loads(args.labels.read_text())
    rows = []
    inputs = []
    for source, spec in labels["sources"].items():
        manifest_path = ROOT / spec["review"] / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        video = ROOT / VIDEOS[source]
        if file_sha256(video) != manifest["source_sha256"]:
            raise ValueError(f"Source mismatch: {source}")
        capture = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG,
                                   [cv2.CAP_PROP_N_THREADS, 1])
        fps = capture.get(cv2.CAP_PROP_FPS)
        shot_rows = []
        for shot in manifest["shots"]:
            frames = []
            for t in shot["frame_times_s"]:
                capture.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError(f"Decode failed: {source} {t}")
                frames.append(frame)
            shot_rows.append({"source": source, "shot_id": shot["id"],
                              "interval_s": shot["interval_s"],
                              "label": spec["labels"][shot["id"]],
                              "feature": shot_features(frames),
                              "overlay_fraction": sum(compact_overlay_visible(frame)
                                                      for frame in frames) / 3})
        capture.release()
        blank = np.zeros_like(shot_rows[0]["feature"])
        for index, row in enumerate(shot_rows):
            following = shot_rows[index + 1] if index + 1 < len(shot_rows) else None
            following_feature = following["feature"] if following else blank
            next_live = following["overlay_fraction"] if following else 0
            row["pair_feature"] = np.concatenate((row["feature"], following_feature,
                                                   [row["overlay_fraction"], next_live]))
            row["phase_supported"] = row["overlay_fraction"] >= 2 / 3 or next_live >= 2 / 3
            del row["feature"]
            rows.append(row)
        inputs.append({"source": source, "manifest_sha256": file_sha256(manifest_path),
                       "video_sha256": file_sha256(video)})
    args.output.mkdir(parents=True)
    folds = []
    for heldout in labels["sources"]:
        fit = [row for row in rows if row["source"] != heldout]
        test = [row for row in rows if row["source"] == heldout]
        x_fit = np.stack([row["pair_feature"] for row in fit])
        y_fit = np.asarray([row["label"] for row in fit])
        scaler = StandardScaler().fit(x_fit)
        model = LogisticRegression(C=0.05, class_weight="balanced", max_iter=5000,
                                   random_state=9031).fit(scaler.transform(x_fit), y_fit)
        p = model.predict_proba(scaler.transform(
            np.stack([row["pair_feature"] for row in test])))[:, 1]
        evaluated = [{"source": heldout, "shot_id": row["shot_id"],
                      "interval_s": row["interval_s"], "label": row["label"],
                      "probability": float(probability),
                      "phase_supported": row["phase_supported"],
                      "predicted": int(probability >= 0.5 and row["phase_supported"])}
                     for row, probability in zip(test, p)]
        model_path = args.output / f"model-excluding-{heldout}.npz"
        np.savez_compressed(model_path, mean=scaler.mean_, scale=scaler.scale_,
                            weights=model.coef_, intercept=model.intercept_)
        folds.append({"heldout": heldout, "score": score(evaluated),
                      "model_sha256": file_sha256(model_path), "rows": evaluated})
    result = {
        "status": "postscore_development_shot_pair_and_phase_transfer_probe",
        "labels_sha256": file_sha256(args.labels), "inputs": inputs,
        "feature_code_sha256": file_sha256(ROOT / "prototype/shot_origin_model.py"),
        "runner_sha256": file_sha256(__file__),
        "model_specification": "Current and following three-frame shot features, balanced logistic regression C=0.05, 0.5 probability threshold, then live overlay in either shot",
        "folds": folds, "pooled": score([row for fold in folds for row in fold["rows"]]),
        "limitations": [
            "Pairing and phase condition were designed after inspecting the first three-fold failure, including Swiss break errors.",
            "No independent held-out shot or throw-event score follows from this postscore probe.",
            "A live overlay and delivery-looking shot still do not verify stone release or identity.",
        ],
    }
    (args.output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({fold["heldout"]: fold["score"] for fold in folds}, indent=2))


if __name__ == "__main__":
    main()
