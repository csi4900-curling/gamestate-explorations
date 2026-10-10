"""Fit a development right-view patch model with leave-one-match-out checks."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cap_patch_verifier import context_bbox
from stone_patch_detector import patch_features

BASE = ROOT / "validation/throw-event-benchmark"
SELECTION = BASE / "right-sideview-source-diverse-development-v1/selection.json"
MODEL = SELECTION.parent / "model.npz"
OUT = SELECTION.parent / "training-results.json"
MATCHES = ("italy", "estonia", "usa")


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def fit(samples):
    x = np.stack([sample["features"] for sample in samples])
    y = np.asarray([sample["label"] for sample in samples])
    if set(y) != {0, 1}:
        raise ValueError("Training split lacks a class")
    scaler = StandardScaler().fit(x)
    model = LinearSVC(C=0.1, class_weight="balanced", max_iter=5000, random_state=9031).fit(
        scaler.transform(x), y
    )
    return scaler, model


def score_examples(examples, feature_by_key, scaler, model):
    rows = []
    for example in examples:
        scores = [
            float(
                model.decision_function(
                    scaler.transform(
                        feature_by_key[
                            (example["match"], sample["time_s"], tuple(sample["cap_bbox_px"]))
                        ][None, :]
                    )
                )[0]
            )
            for sample in example["samples"]
        ]
        rows.append(
            {
                "example_id": example["example_id"],
                "match": example["match"],
                "source_pixel_class": example["training_pixel_class"],
                "sample_scores": [round(score, 6) for score in scores],
                "any_positive_patch": any(score >= 0 for score in scores),
                "mean_positive_patch": float(np.mean(scores)) >= 0,
            }
        )
    return rows


def main():
    if MODEL.exists() or OUT.exists():
        raise ValueError("Development model or results already exist")
    selection = json.loads(SELECTION.read_text())
    if selection["example_count"] != len(selection["examples"]) or {
        e["match"] for e in selection["examples"]
    } != set(MATCHES):
        raise ValueError("Selection inventory differs")
    sources = {source["inventory"]: source for source in selection["sources"]}
    for source in sources.values():
        for key in ("video", "scan", "review"):
            if digest(BASE / source[key]) != source[key + "_sha256"]:
                raise ValueError(f"Training source changed: {source['inventory']}")
    feature_by_key = {}
    label_by_key = {}
    for match in MATCHES:
        inventories = [source for source in sources.values() if source["match"] == match]
        if len({source["video_sha256"] for source in inventories}) != 1:
            raise ValueError("Match source videos differ")
        video = BASE / inventories[0]["video"]
        capture = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
        fps = capture.get(cv2.CAP_PROP_FPS)
        if not capture.isOpened() or fps <= 0:
            raise ValueError("Source video unreadable")
        try:
            for example in (e for e in selection["examples"] if e["match"] == match):
                label = int(example["training_pixel_class"] == "stone_pixels")
                for sample in example["samples"]:
                    key = (match, sample["time_s"], tuple(sample["cap_bbox_px"]))
                    if key in label_by_key:
                        if label_by_key[key] != label:
                            raise ValueError("Conflicting source-pixel classes on one crop")
                        continue
                    capture.set(cv2.CAP_PROP_POS_FRAMES, round(sample["time_s"] * fps))
                    ok, frame = capture.read()
                    if not ok or frame.shape[:2] != (360, 640):
                        raise ValueError(f"Cannot decode {example['example_id']}")
                    feature_by_key[key] = patch_features(frame, context_bbox(sample["cap_bbox_px"]))
                    label_by_key[key] = label
        finally:
            capture.release()
    sample_rows = [
        {"key": key, "match": key[0], "features": features, "label": label_by_key[key]}
        for key, features in feature_by_key.items()
    ]
    fold_rows = []
    for heldout in MATCHES:
        scaler, model = fit([r for r in sample_rows if r["match"] != heldout])
        scored = score_examples(
            [e for e in selection["examples"] if e["match"] == heldout],
            feature_by_key,
            scaler,
            model,
        )
        counts = Counter((r["source_pixel_class"], r["any_positive_patch"]) for r in scored)
        fold_rows.append(
            {
                "heldout_match": heldout,
                "training_match_names": [m for m in MATCHES if m != heldout],
                "training_unique_crop_count": sum(r["match"] != heldout for r in sample_rows),
                "source_class_by_any_positive_patch": {
                    cls: {"positive": counts[cls, True], "negative": counts[cls, False]}
                    for cls in ("stone_pixels", "person_or_equipment_pixels")
                },
                "rows": scored,
            }
        )
    scaler, model = fit(sample_rows)
    np.savez_compressed(
        MODEL,
        mean=scaler.mean_,
        scale=scaler.scale_,
        weights=model.coef_,
        intercept=model.intercept_,
        threshold=np.asarray(0.0),
    )
    fit_rows = score_examples(selection["examples"], feature_by_key, scaler, model)
    counts = Counter((r["source_pixel_class"], r["any_positive_patch"]) for r in fit_rows)
    result = {
        "status": "development_2024_multimatch_source_pixel_patch_model_not_event_detector",
        "selection_sha256": digest(SELECTION),
        "model_sha256": digest(MODEL),
        "feature_code_sha256": digest(ROOT / "prototype/stone_patch_detector.py"),
        "crop_code_sha256": digest(ROOT / "prototype/cap_patch_verifier.py"),
        "runner_sha256": digest(Path(__file__)),
        "fit_method": "StandardScaler + LinearSVC(C=0.1, class_weight=balanced, random_state=9031), zero threshold",
        "training_matches": list(MATCHES),
        "training_example_count": len(selection["examples"]),
        "unique_training_crop_count": len(sample_rows),
        "leave_one_match_out": fold_rows,
        "fit_source_class_by_any_positive_patch": {
            cls: {"positive": counts[cls, True], "negative": counts[cls, False]}
            for cls in ("stone_pixels", "person_or_equipment_pixels")
        },
        "limitations": [
            "All labels are selected same-agent source-pixel judgments, not independent physical throw labels.",
            "Some paths overlap within a match; leave-one-match-out prevents video leakage across folds but path counts remain correlated.",
            "No Latvia sample enters fitting, but Latvia results were already inspected before this development model was specified.",
            "Patch identity cannot establish delivery, release, settle, full-match recall or simulation readiness.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "unique_crops": len(sample_rows),
                "folds": [r["source_class_by_any_positive_patch"] for r in fold_rows],
            }
        )
    )


if __name__ == "__main__":
    main()
