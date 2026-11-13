"""Apply frozen delivery-shot pair weights to a source interval."""

import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from learned_gap_confirmation import compact_overlay_visible
from scripts.score_shot_origin_transfer import score
from shot_origin_model import shot_features


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument(
        "--labels", type=Path, help="Optional source-only development labels for scoring"
    )
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first frozen score")
    manifest = json.loads((args.review / "manifest.json").read_text())
    labels = json.loads(args.labels.read_text()) if args.labels else None
    digest = file_sha256(args.video)
    if digest != manifest["source_sha256"] or (
        labels is not None and digest != labels["source_sha256"]
    ):
        parser.error("Source fingerprint mismatch")
    if labels is not None and set(labels["labels"]) != {shot["id"] for shot in manifest["shots"]}:
        parser.error("Shot label set incomplete")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if digest == reserved["source_sha256"]:
        parser.error("Reserved source cannot be used for development")
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    for shot in manifest["shots"]:
        frames = []
        for t in shot["frame_times_s"]:
            capture.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Frame decode failed at {t}")
            frames.append(frame)
        rows.append(
            {
                "shot_id": shot["id"],
                "interval_s": shot["interval_s"],
                "label": labels["labels"][shot["id"]] if labels else None,
                "feature": shot_features(frames),
                "overlay_fraction": sum(compact_overlay_visible(frame) for frame in frames) / 3,
            }
        )
    capture.release()
    blank = np.zeros_like(rows[0]["feature"])
    features = []
    for index, row in enumerate(rows):
        following = rows[index + 1] if index + 1 < len(rows) else None
        next_feature = following["feature"] if following else blank
        next_live = following["overlay_fraction"] if following else 0
        features.append(
            np.concatenate((row["feature"], next_feature, [row["overlay_fraction"], next_live]))
        )
        row["phase_supported"] = row["overlay_fraction"] >= 2 / 3 or next_live >= 2 / 3
        del row["feature"]
    with np.load(args.model, allow_pickle=False) as model:
        x = (np.stack(features) - model["mean"]) / model["scale"]
        logits = x @ model["weights"].ravel() + model["intercept"].item()
        probabilities = 1 / (1 + np.exp(-np.clip(logits, -40, 40)))
    for row, probability in zip(rows, probabilities):
        row["probability"] = float(probability)
        row["predicted"] = int(probability >= 0.5 and row["phase_supported"])
    resolved = [row for row in rows if row["label"] in (0, 1)]
    result = {
        "status": "frozen_shot_origin_inference"
        if labels is None
        else "first_frozen_live_match_interval_shot_origin_transfer",
        "source_sha256": digest,
        "source_interval_s": manifest["source_interval_s"],
        "review_manifest_sha256": file_sha256(args.review / "manifest.json"),
        "labels_sha256": file_sha256(args.labels) if args.labels else None,
        "model_sha256": file_sha256(args.model),
        "feature_code_sha256": file_sha256(ROOT / "prototype/shot_origin_model.py"),
        "runner_sha256": file_sha256(__file__),
        "score_resolved_shots": score(resolved) if resolved else None,
        "resolved_shot_count": len(resolved),
        "unresolved_shot_count": len(rows) - len(resolved),
        "rows": rows,
        "limitations": [
            "The source may be exposed development footage; inference alone supplies no event F1.",
            "Optional labels are agent-authored from three frames per shot, not independent event truth.",
            "Shot-origin classification is one cue, not proof of release, colour, or physical trajectory.",
        ],
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "resolved": result["score_resolved_shots"],
                "unresolved": result["unresolved_shot_count"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
