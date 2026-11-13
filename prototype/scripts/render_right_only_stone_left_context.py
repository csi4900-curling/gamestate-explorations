"""Show left-camera context around source-reviewed right-only moving stones."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np


def digest(path):
    result = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "inventory", "source_review", "output_dir"):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists")
    inventory = json.loads(args.inventory.read_text())
    review = json.loads(args.source_review.read_text())
    if inventory["source_sha256"] != review["source_sha256"] or inventory[
        "source_sha256"
    ] != digest(args.video):
        parser.error("Source fingerprints differ")
    review_ids = {
        r["raw_track_id"] for r in review["rows"] if r["source_prefix_class"] == "moving_stone"
    }
    rows = [
        r
        for r in inventory["rows"]
        if r["raw_track_id"] in review_ids
        and r["temporal_status"] == "no_left_time_colour_candidate"
    ]
    if len(rows) != len(review_ids):
        parser.error("Moving-stone review IDs do not map one-to-one")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    sheet = np.full((390 * len(rows), 1600, 3), 20, dtype=np.uint8)
    manifest_rows = []
    try:
        for row_index, row in enumerate(rows):
            t = row["passage_time_s"]
            samples = []
            for col, offset in enumerate((-15, -10, -5, 0, 5)):
                source_t = t + offset
                frame_index = round(source_t * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f"Could not decode {source_t:.3f} s")
                resized = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
                left = resized[:, :320]
                top, x = row_index * 390, col * 320
                sheet[top + 20 : top + 380, x : x + 320] = left
                cv2.putText(
                    sheet,
                    f"{row['proposal_id']} {source_t:.1f}s",
                    (x + 5, top + 16),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.43,
                    (255, 255, 255),
                    1,
                )
                samples.append(
                    {"source_time_s": round(source_t, 3), "decoded_frame_index": frame_index}
                )
            manifest_rows.append(
                {
                    "proposal_id": row["proposal_id"],
                    "right_passage_time_s": t,
                    "sheet": "sheet-01.jpg",
                    "samples": samples,
                }
            )
    finally:
        cap.release()
    args.output_dir.mkdir(parents=True)
    path = args.output_dir / "sheet-01.jpg"
    if not cv2.imwrite(str(path), sheet):
        raise RuntimeError(f"Could not write {path}")
    result = {
        "status": "left_context_for_right_only_source_visible_stones_not_delivery_truth",
        "source_sha256": inventory["source_sha256"],
        "inventory_sha256": digest(args.inventory),
        "source_review_sha256": digest(args.source_review),
        "runner_sha256": digest(Path(__file__)),
        "rows": manifest_rows,
        "sheets": [{"file": "sheet-01.jpg", "sha256": digest(path)}],
        "limitations": [
            "Five widely spaced left frames cannot prove or exclude a brief release.",
            "The right path's physical delivery identity remains unverified.",
        ],
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"right_only_stone_paths": len(rows)}))


if __name__ == "__main__":
    main()
