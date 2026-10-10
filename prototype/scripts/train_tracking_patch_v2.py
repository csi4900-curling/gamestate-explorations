"""Train and clip-split test a stone patch model on public tracking videos.

This is an object-box development study, not a throw-event or match-independent
benchmark. Clip 0 was inspected before this split and is forced into training.
"""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import random
import subprocess
import sys

import cv2
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from box_evaluation import iou, score_boxes
from scripts.score_public_tracking_clip_boxes import reference_boxes
from stone_patch_detector import (colour_proposals, detect_stones, load_model,
                                  patch_features, select_boxes)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clip_id(path):
    return int(path.stem.rsplit("_", 1)[1])


def clip_frames(dataset, number, step):
    video = dataset / "videos" / f"curling_vedio_{number}.mp4"
    labels = dataset / "labels" / f"curling_vedio_{number}"
    capture = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        raise ValueError(f"Cannot open {video}")
    frame_count = round(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    for index in range(0, frame_count, step):
        label_path = labels / f"{index:08d}.txt"
        if not label_path.exists():
            continue
        capture.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = capture.read()
        if not ok:
            raise RuntimeError(f"Decode failed in clip {number} frame {index}")
        yield index, frame, reference_boxes(label_path)
    capture.release()


def training_data(dataset, clips, step, max_negatives):
    features, targets = [], []
    counts = Counter()
    for number in clips:
        for frame_index, frame, reference in clip_frames(dataset, number, step):
            image, proposals = colour_proposals(frame)
            for row in reference:
                features.append(patch_features(image, row["bbox"]))
                targets.append(1)
                counts["reference_positive"] += 1
            negatives = []
            for proposal in proposals:
                same = max((iou(proposal["bbox"], row["bbox"])
                            for row in reference if row["colour"] == proposal["colour"]),
                           default=0)
                any_colour = max((iou(proposal["bbox"], row["bbox"])
                                  for row in reference), default=0)
                if same >= 0.5:
                    features.append(patch_features(image, proposal["bbox"]))
                    targets.append(1)
                    counts["proposal_positive"] += 1
                elif any_colour < 0.2:
                    negatives.append(proposal)
                else:
                    counts["ignored_overlap"] += 1
            random.Random(9031 + number * 100000 + frame_index).shuffle(negatives)
            for proposal in negatives[:max_negatives]:
                features.append(patch_features(image, proposal["bbox"]))
                targets.append(0)
                counts["negative"] += 1
            counts["frames"] += 1
    return np.asarray(features, np.float32), np.asarray(targets, np.int8), dict(counts)


def validation_proposals(dataset, clips, step, scaler, classifier):
    rows = []
    for number in clips:
        for frame_index, frame, reference in clip_frames(dataset, number, step):
            image, proposals = colour_proposals(frame)
            if proposals:
                features = np.stack([patch_features(image, row["bbox"])
                                     for row in proposals])
                scores = classifier.decision_function(scaler.transform(features))
            else:
                scores = []
            rows.append({"clip_id": number, "frame_index": frame_index,
                         "reference": reference, "proposals": proposals,
                         "scores": [float(value) for value in scores]})
    return rows


def total_score(records, threshold):
    total = Counter()
    for row in records:
        predicted = select_boxes(row["proposals"], row["scores"], threshold)
        score = score_boxes(row["reference"], predicted)
        total.update({key: score[key] for key in
                      ("references", "predictions", "matches", "misses", "extras")})
    tp, fp, fn = total["matches"], total["extras"], total["misses"]
    return {**dict(total),
            "precision": round(tp / (tp + fp), 4) if tp + fp else None,
            "recall": round(tp / (tp + fn), 4) if tp + fn else None,
            "f1": round(2 * tp / (2 * tp + fp + fn), 4)
            if 2 * tp + fp + fn else None}


def evaluate_model(dataset, clips, step, model):
    aggregate = Counter()
    by_clip = []
    for number in clips:
        local = Counter()
        frames = 0
        for _, frame, reference in clip_frames(dataset, number, step):
            score = score_boxes(reference, detect_stones(frame, model))
            local.update({key: score[key] for key in
                          ("references", "predictions", "matches", "misses", "extras")})
            frames += 1
        aggregate.update(local)
        tp, fp, fn = local["matches"], local["extras"], local["misses"]
        by_clip.append({"clip_id": number, "sampled_frames": frames,
                        **dict(local),
                        "box_f1": round(2 * tp / (2 * tp + fp + fn), 4)
                        if 2 * tp + fp + fn else None})
    tp, fp, fn = aggregate["matches"], aggregate["extras"], aggregate["misses"]
    return {"totals": {**dict(aggregate),
                       "precision": round(tp / (tp + fp), 4) if tp + fp else None,
                       "recall": round(tp / (tp + fn), 4) if tp + fn else None,
                       "f1": round(2 * tp / (2 * tp + fp + fn), 4)
                       if 2 * tp + fp + fn else None},
            "clips": by_clip}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--baseline-model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--train-step", type=int, default=25)
    parser.add_argument("--eval-step", type=int, default=5)
    parser.add_argument("--max-negatives", type=int, default=40)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first clip-split result")
    paths = sorted((args.dataset / "videos").glob("curling_vedio_*.mp4"),
                   key=clip_id)
    ids = [clip_id(path) for path in paths]
    if len(ids) != len(set(ids)) or len(ids) < 40 or 0 not in ids:
        parser.error("Expected at least 40 uniquely numbered public tracking clips")
    rng = random.Random(9031)
    others = [number for number in ids if number != 0]
    rng.shuffle(others)
    test_ids = sorted(others[:20])
    validation_ids = sorted(others[20:35])
    fit_ids = sorted([0, *others[35:]])
    fit_x, fit_y, fit_counts = training_data(
        args.dataset, fit_ids, args.train_step, args.max_negatives)
    scaler = StandardScaler().fit(fit_x)
    classifier = LinearSVC(C=0.1, class_weight="balanced", max_iter=5000,
                           random_state=9031)
    classifier.fit(scaler.transform(fit_x), fit_y)
    del fit_x, fit_y
    validation = validation_proposals(
        args.dataset, validation_ids, args.train_step, scaler, classifier)
    pool = np.asarray([score for row in validation for score in row["scores"]])
    thresholds = sorted(set(float(value) for value in
                            np.quantile(pool, np.linspace(0.5, 0.995, 40))))
    candidates = [{"threshold": threshold,
                   "score": total_score(validation, threshold)}
                  for threshold in thresholds]
    selected = max(candidates, key=lambda row: (row["score"]["f1"] or 0,
                                                 row["threshold"]))
    args.output.mkdir(parents=True)
    model_path = args.output / "model.npz"
    np.savez_compressed(model_path, mean=scaler.mean_, scale=scaler.scale_,
                        weights=classifier.coef_, intercept=classifier.intercept_,
                        threshold=selected["threshold"])
    updated = evaluate_model(args.dataset, test_ids, args.eval_step,
                             load_model(model_path))
    baseline = evaluate_model(args.dataset, test_ids, args.eval_step,
                              load_model(args.baseline_model))
    git_root = args.dataset.parents[1]
    commit = subprocess.run(["git", "-C", str(git_root), "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip()
    source_hashes = {str(number): digest(args.dataset / "videos" /
                                          f"curling_vedio_{number}.mp4")
                     for number in test_ids}
    label_coverage = {}
    for number in test_ids:
        video = args.dataset / "videos" / f"curling_vedio_{number}.mp4"
        capture = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG,
                                   [cv2.CAP_PROP_N_THREADS, 1])
        sampled = len(range(0, round(capture.get(cv2.CAP_PROP_FRAME_COUNT)), args.eval_step))
        capture.release()
        labelled = sum(1 for row in updated["clips"] if row["clip_id"] == number
                       for _ in range(row["sampled_frames"]))
        label_coverage[str(number)] = {"possible_frames": sampled,
                                       "labelled_frames": labelled}
    result = {
        "status": "clip_split_public_tracking_stone_box_development_not_throw_f1",
        "dataset_source": "https://github.com/CurlObserver/dataset",
        "dataset_commit": commit,
        "clip_count": len(ids),
        "fit_clip_ids": fit_ids,
        "validation_clip_ids": validation_ids,
        "test_clip_ids": test_ids,
        "test_video_sha256_by_clip": source_hashes,
        "test_sampled_label_coverage": label_coverage,
        "train_frame_step": args.train_step,
        "test_frame_step": args.eval_step,
        "fit_patch_counts": fit_counts,
        "validation_threshold_choice": selected,
        "baseline_model_sha256": digest(args.baseline_model),
        "new_model_sha256": digest(model_path),
        "feature_code_sha256": digest(ROOT / "prototype/stone_patch_detector.py"),
        "runner_sha256": digest(Path(__file__)),
        "baseline_test": baseline,
        "new_model_test": updated,
        "limitations": [
            "Public clip IDs do not reveal source matches; test clips may share broadcasts with fit clips or the baseline model's public training images.",
            "Frame-level boxes are temporally correlated and do not score persistent stone identity.",
            "This does not measure full-match throw-event precision, recall, colour-aware F1, or camera-handoff correctness.",
            "Clip 0 was inspected before splitting and is included only in training.",
            "Frames with missing public annotation files are excluded from fit and scoring; sampled test coverage is recorded per clip.",
        ],
    }
    (args.output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print({"validation": selected["score"],
           "baseline_test": baseline["totals"],
           "new_model_test": updated["totals"]})


if __name__ == "__main__":
    main()
