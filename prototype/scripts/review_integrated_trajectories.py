"""Reproducible source contact sheets for all newly associated camera segments."""

import argparse
import json
from pathlib import Path
import sys
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256


def build(video, aggregate, output):
    data = json.loads(aggregate.read_text())
    if file_sha256(video) != data["context"]["source_sha256"]:
        raise ValueError("Source mismatch")
    cap = cv2.VideoCapture(str(video))
    output.mkdir(parents=True, exist_ok=True)
    entries = []
    pages = []
    tiles = []
    for event in data["events"]:
        for segment in event["segments"]:
            points = segment["pixel_points"]
            if not points:
                continue
            # Review every new segment; departure segments already reviewed in v1 stay separately identified.
            if segment.get("camera") == "left_split":
                continue
            chosen = [points[i] for i in (0, len(points) // 2, len(points) - 1)]
            row = np.full((170, 800, 3), 245, np.uint8)
            for j, p in enumerate(chosen):
                cap.set(cv2.CAP_PROP_POS_MSEC, p["time_s"] * 1000)
                ok, frame = cap.read()
                if not ok:
                    raise ValueError(f"Cannot decode {p['time_s']}")
                frame = cv2.resize(frame, (640, 360))
                x, y = p["pixel"]
                crop = cv2.getRectSubPix(frame, (100, 75), (float(x), float(y)))
                crop = cv2.resize(crop, (200, 150), interpolation=cv2.INTER_NEAREST)
                row[20:170, 200 + j * 200 : 400 + j * 200] = crop
                cv2.putText(
                    row,
                    f"{p['time_s']:.2f}",
                    (200 + j * 200, 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (0, 0, 0),
                    1,
                )
                if j == 1:
                    row[40:152, :200] = cv2.resize(frame, (200, 112))
            key = segment["segment_id"]
            cv2.putText(row, key, (3, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
            entries.append(
                {
                    "candidate_id": event["candidate_id"],
                    "segment_id": key,
                    "camera": segment["camera"],
                    "role": segment["role"],
                    "checkpoints": chosen,
                    "sheet": f"sheet-{len(entries) // 6:03}.jpg",
                    "stone_at_checkpoints": None,
                    "same_delivered_stone": None,
                }
            )
            tiles.append(row)
            if len(tiles) == 6:
                target = output / f"sheet-{len(pages):03}.jpg"
                cv2.imwrite(str(target), np.vstack(tiles))
                pages.append(target.name)
                tiles = []
    if tiles:
        target = output / f"sheet-{len(pages):03}.jpg"
        cv2.imwrite(str(target), np.vstack(tiles))
        pages.append(target.name)
    cap.release()
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "source_sha256": file_sha256(video),
                "aggregate_sha256": file_sha256(aggregate),
                "method": "Every newly associated segment, first/middle/last source crops at predicted location. Null labels require actual review.",
                "rows": entries,
                "sheets": pages,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"{len(entries)} segments, {len(pages)} sheets")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--aggregate", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    build(a.video, a.aggregate, a.output)
