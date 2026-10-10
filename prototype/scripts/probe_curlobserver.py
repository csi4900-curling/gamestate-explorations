"""Deterministic published-label smoke benchmark of the frozen colour proposal stage.
Not an evaluation of the calibrated body detector or complete throw pipeline.
"""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import urllib.request
import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from throw_detection import PassageConfig, stone_candidates
from box_evaluation import score_boxes

REVISION = "2cfe61efede3c446957ee94aefa8df1345fc4684"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    config = PassageConfig(roi=(0, 0, 640, 360))
    indices = [round(i * 4999 / 24) for i in range(25)]
    manifest = {
        "status": "published_label_component_smoke_test",
        "revision": REVISION,
        "sample_indices": indices,
        "selection": "25 evenly spaced image indices selected before downloading or inference",
        "config": asdict(config),
        "iou_threshold": 0.5,
        "matching": "one-to-one same-colour maximum-cardinality matching at IoU >= 0.5",
        "model_sha256": file_sha256(ROOT / "prototype/throw_detection.py"),
        "runner_sha256": file_sha256(__file__),
        "adaptation": "Full-image ROI to test stone proposals; all colour/size/body thresholds unchanged.",
        "provenance": "Publisher labels, not authored here. Not an official held-out split; match-level overlap with previous Olympic development images is unverified.",
    }
    (a.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    results = []
    for n in indices:
        for kind, suffix in [("images", "jpg"), ("labels", "txt")]:
            path = f"curling_dataset/curling_detect_dataset/{kind}/{n:04d}.{suffix}"
            url = f"https://raw.githubusercontent.com/CurlObserver/dataset/{REVISION}/{path}"
            target = a.output / f"{n:04d}.{suffix}"
            with urllib.request.urlopen(url, timeout=40) as response:
                target.write_bytes(response.read())
        frame = cv2.imread(str(a.output / f"{n:04d}.jpg"))
        if frame is None:
            raise ValueError("Unreadable benchmark image")
        reference = []
        for line in (a.output / f"{n:04d}.txt").read_text().splitlines():
            fields = list(map(float, line.split()))
            if len(fields) != 5:
                raise ValueError("Unsupported label format")
            label, x, y, w, h = fields
            if label not in (0, 1) or not all(0 <= v <= 1 for v in (x, y, w, h)) or min(w, h) <= 0:
                raise ValueError("Invalid YOLO label")
            reference.append(
                {
                    "colour": ("red", "yellow")[int(label)],
                    "bbox": [(x - w / 2) * 640, (y - h / 2) * 360, w * 640, h * 360],
                }
            )
        predicted = stone_candidates(frame, config)
        row = {
            "index": n,
            "image_sha256": file_sha256(a.output / f"{n:04d}.jpg"),
            "labels_sha256": file_sha256(a.output / f"{n:04d}.txt"),
            "reference": reference,
            "predicted": predicted,
            "score": score_boxes(reference, predicted),
        }
        results.append(row)
        print(n, row["score"], flush=True)
    total = {
        key: sum(row["score"][key] for row in results)
        for key in ["references", "predictions", "matches", "misses", "extras"]
    }
    total["precision"] = total["matches"] / total["predictions"] if total["predictions"] else None
    total["recall"] = total["matches"] / total["references"] if total["references"] else None
    (a.output / "results.json").write_text(
        json.dumps(dict(manifest, totals=total, images=results), indent=2, allow_nan=False) + "\n"
    )
    print(json.dumps(total))


if __name__ == "__main__":
    main()
