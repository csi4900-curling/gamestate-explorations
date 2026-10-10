"""Score a source-linked cap packet with existing frozen patch weights."""

import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from stone_patch_detector import load_model, patch_features


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve the first frozen score")
    manifest_path = args.packet / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    model = load_model(args.model)
    rows = []
    for event in manifest["rows"]:
        scores = []
        for sample in event["samples"]:
            path = args.packet / sample["crop_path"]
            if file_sha256(path) != sample["crop_sha256"]:
                raise ValueError(f"Crop hash mismatch: {path}")
            image = cv2.imread(str(path))
            if image is None or image.shape[:2] != (48, 48):
                raise ValueError(f"Unreadable 48-pixel crop: {path}")
            feature = patch_features(image, [0, 0, 48, 48])
            score = ((feature - model["mean"]) / model["scale"]) @ model["weights"].ravel()
            score += model["intercept"].item()
            scores.append(float(score))
        mean_score = float(np.mean(scores))
        rows.append({
            "source_id": event["source_id"],
            "event_id": event["event_id"],
            "source_review": event["source_review"],
            "sample_scores": [round(value, 6) for value in scores],
            "mean_score": round(mean_score, 6),
            "predicted_stone_like": bool(mean_score >= float(model["threshold"])),
        })
    result = {
        "status": "development_frozen_patch_transfer",
        "packet_manifest_sha256": file_sha256(manifest_path),
        "model_sha256": file_sha256(args.model),
        "feature_code_sha256": file_sha256(ROOT / "prototype/stone_patch_detector.py"),
        "runner_sha256": file_sha256(__file__),
        "event_aggregation": "mean_of_three_sample_decision_scores",
        "threshold": float(model["threshold"]),
        "rows": rows,
        "stone_like_count": sum(row["predicted_stone_like"] for row in rows),
        "limitations": manifest["limitations"] + [
            "Scores are patch appearance evidence, not proof of a newly delivered stone.",
            "No independent full-video throw precision or recall follows from this selected packet.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"stone_like": result["stone_like_count"], "tracks": len(rows)}))


if __name__ == "__main__":
    main()
