"""Train a CPU patch classifier for public stone-box proposals.

Image-level validation is only a development diagnostic: source matches are
unknown, and this is not an end-to-end throw-event benchmark.
"""

import argparse
import json
from pathlib import Path
import random
import sys

import cv2
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from box_evaluation import iou, score_boxes
from cache_contract import file_sha256
from stone_patch_detector import colour_proposals, patch_features, select_boxes


def labels(path):
    rows = []
    for line in path.read_text().splitlines():
        fields = list(map(float, line.split()))
        if len(fields) != 5 or fields[0] not in (0, 1):
            raise ValueError(f"Invalid publisher box: {path}")
        category, x, y, width, height = fields
        rows.append(
            {
                "colour": ("red", "yellow")[int(category)],
                "bbox": [(x - width / 2) * 640, (y - height / 2) * 360, width * 640,
                         height * 360],
            }
        )
    return rows


def image_data(directory, index):
    frame = cv2.imread(str(directory / f"{index:04d}.jpg"))
    if frame is None:
        raise ValueError(f"Unreadable publisher image {index}")
    image, proposals = colour_proposals(frame)
    reference = labels(directory / f"{index:04d}.txt")
    features = np.stack([patch_features(image, row["bbox"]) for row in proposals]) if proposals else None
    return image, proposals, reference, features


def training_rows(directory, indices):
    features, targets = [], []
    counters = {"positive": 0, "negative": 0, "ignored": 0}
    for index in indices:
        image, proposals, reference, proposal_features = image_data(directory, index)
        for row in reference:
            features.append(patch_features(image, row["bbox"]))
            targets.append(1)
            counters["positive"] += 1
        for proposal, descriptor in zip(proposals, proposal_features if proposal_features is not None else []):
            best_any = max((iou(proposal["bbox"], row["bbox"]) for row in reference), default=0)
            best_same = max(
                (iou(proposal["bbox"], row["bbox"]) for row in reference
                 if row["colour"] == proposal["colour"]),
                default=0,
            )
            if best_same >= 0.5:
                target = 1
            elif best_any < 0.2:
                target = 0
            else:
                counters["ignored"] += 1
                continue
            features.append(descriptor)
            targets.append(target)
            counters["positive" if target else "negative"] += 1
    return np.asarray(features, np.float32), np.asarray(targets, np.int8), counters


def predict_images(directory, indices, scaler, classifier):
    records = []
    for index in indices:
        _, proposals, reference, features = image_data(directory, index)
        scores = classifier.decision_function(scaler.transform(features)) if features is not None else []
        records.append({"index": index, "reference": reference, "proposals": proposals,
                        "scores": [float(score) for score in scores]})
    return records


def evaluate(records, threshold):
    totals = {"references": 0, "predictions": 0, "matches": 0, "misses": 0, "extras": 0}
    per_image = []
    for record in records:
        predicted = select_boxes(record["proposals"], record["scores"], threshold)
        score = score_boxes(record["reference"], predicted)
        for key in totals:
            totals[key] += score[key]
        per_image.append({"index": record["index"], "score": score, "predicted": predicted})
    tp, fp, fn = totals["matches"], totals["extras"], totals["misses"]
    totals.update(
        precision=tp / (tp + fp) if tp + fp else None,
        recall=tp / (tp + fn) if tp + fn else None,
        f1=2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
    )
    return totals, per_image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; preserve the first evaluation")
    manifest = json.loads((args.train / "manifest.json").read_text())
    indices = list(manifest["indices"])
    rng = random.Random(9031)
    rng.shuffle(indices)
    split = round(len(indices) * 0.8)
    fit_indices, validation_indices = indices[:split], indices[split:]
    if set(indices) & set(json.loads((args.probe / "manifest.json").read_text())["sample_indices"]):
        parser.error("Training sample intersects the fixed probe")
    fit_x, fit_y, fit_counts = training_rows(args.train, fit_indices)
    scaler = StandardScaler().fit(fit_x)
    classifier = LinearSVC(C=0.1, class_weight="balanced", max_iter=5000, random_state=9031)
    classifier.fit(scaler.transform(fit_x), fit_y)
    del fit_x, fit_y
    validation = predict_images(args.train, validation_indices, scaler, classifier)
    pool = np.asarray([score for row in validation for score in row["scores"]])
    thresholds = sorted(set(float(value) for value in np.quantile(pool, np.linspace(0.5, 0.995, 40))))
    threshold_scores = []
    for threshold in thresholds:
        totals, _ = evaluate(validation, threshold)
        threshold_scores.append({"threshold": threshold, "totals": totals})
    selected = max(threshold_scores, key=lambda row: (row["totals"]["f1"] or 0, row["threshold"]))
    probe_manifest = json.loads((args.probe / "manifest.json").read_text())
    probe = predict_images(args.probe, probe_manifest["sample_indices"], scaler, classifier)
    probe_totals, probe_images = evaluate(probe, selected["threshold"])
    args.output.mkdir(parents=True)
    model_path = args.output / "model.npz"
    np.savez_compressed(
        model_path,
        mean=scaler.mean_, scale=scaler.scale_, weights=classifier.coef_,
        intercept=classifier.intercept_, threshold=selected["threshold"],
    )
    result = {
        "status": "development_stone_patch_box_probe",
        "training_manifest_sha256": file_sha256(args.train / "manifest.json"),
        "fixed_probe_manifest_sha256": file_sha256(args.probe / "manifest.json"),
        "model_sha256": file_sha256(model_path),
        "feature_code_sha256": file_sha256(ROOT / "prototype/stone_patch_detector.py"),
        "runner_sha256": file_sha256(__file__),
        "fit_indices": fit_indices,
        "validation_indices": validation_indices,
        "training_patch_counts": fit_counts,
        "threshold_selection": "Best one-to-one box F1 on the 20% image-level validation subset",
        "validation_thresholds": threshold_scores,
        "chosen_threshold": selected["threshold"],
        "validation_totals": selected["totals"],
        "fixed_probe_totals": probe_totals,
        "fixed_probe_images": probe_images,
        "limitations": [
            "Publisher image indices have no match IDs; image-level validation and the fixed probe may share source matches.",
            "The fixed probe has 25 images and is a development diagnostic, not independent validation.",
            "Box F1 does not measure throw-event F1, identity, ground position or camera-change performance.",
        ],
    }
    (args.output / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"validation": selected["totals"], "fixed_probe": probe_totals}, indent=2))


if __name__ == "__main__":
    main()
