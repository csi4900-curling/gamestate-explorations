"""Score source-reviewed Latvia/Italy crossing crops with the existing frozen model."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from stone_patch_detector import patch_features  # noqa: E402

DEFAULT_PACKET = (
    ROOT / "validation/official-shot-sequence/latvia-italy-crossing-patch-source-class-packet"
)
MODEL = ROOT / "validation/official-shot-sequence/identity-crossing-transfer-v1/model.npz"
DEFAULT_OUTPUT = (
    ROOT
    / "validation/official-shot-sequence/latvia-italy-frozen-crossing-patch-source-class-score.json"
)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    manifest_path = args.packet / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if not all(source["same_video_bytes_as_timeline"] for source in manifest["sources"]):
        raise ValueError("Packet video and event timeline sources differ")
    frozen = np.load(MODEL)
    rows = []
    for event in manifest["rows"]:
        scores = []
        for sample in event["samples"]:
            path = args.packet / sample["crop_path"]
            if digest(path) != sample["crop_sha256"]:
                raise ValueError(f"Patch hash mismatch: {path}")
            image = cv2.imread(str(path))
            if image is None or image.shape[:2] != (48, 48):
                raise ValueError(f"Unexpected crop geometry: {path}")
            features = patch_features(image, [0, 0, 48, 48])
            score = float(
                np.dot((features - frozen["mean"]) / frozen["scale"], frozen["weights"][0])
                + frozen["intercept"][0]
            )
            scores.append(round(score, 6))
        if len(scores) != 3:
            raise ValueError("Expected three crossing-local samples")
        mean_score = round(float(np.mean(scores)), 6)
        rows.append(
            {
                "source_id": event["source_id"],
                "event_id": event["event_id"],
                "source_pixel_class": event["source_review"],
                "source_review_kind": event["review_kind"],
                "sample_scores": scores,
                "mean_score": mean_score,
                "model_positive": mean_score >= float(frozen["threshold"]),
            }
        )
    counts = {}
    for source_class in ("stone_shaped_pixels", "person_pixels"):
        group = [row for row in rows if row["source_pixel_class"] == source_class]
        counts[source_class] = {
            "total": len(group),
            "model_positive": sum(row["model_positive"] for row in group),
        }
    result = {
        "status": "postreview_frozen_patch_source_class_transfer_not_event_validation",
        "packet_manifest_sha256": digest(manifest_path),
        "model_sha256": digest(MODEL),
        "feature_code_sha256": digest(ROOT / "prototype/stone_patch_detector.py"),
        "runner_sha256": digest(Path(__file__)),
        "aggregation": "mean_of_three_crossing_local_scores",
        "threshold": float(frozen["threshold"]),
        "source_pixel_class_counts": counts,
        "rows": rows,
        "limitations": [
            "Source classes are same-agent postproposal pixel reviews, not independent throw labels.",
            "The frozen model has already failed stone retention on Estonia and Italy development samples.",
            "A positive patch score does not establish a physical delivery; a negative score does not disprove one.",
            "This selected set cannot estimate full-match event precision, recall or F1.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(counts)


if __name__ == "__main__":
    main()
