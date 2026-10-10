"""Render every right-only track with three positive frozen patch samples."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "right-tail", "patches", "output-dir"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory exists")
    tail = json.loads(args.right_tail.read_text())
    patches = json.loads(args.patches.read_text())
    if (
        digest(args.video) != tail["source_sha256"]
        or patches["source_sha256"] != tail["source_sha256"]
        or patches["input_sha256"]["right_tail"] != digest(args.right_tail)
    ):
        raise ValueError("Source or tail hash differs")
    selected = [
        row for row in patches["rows"] if row["positive_patch_count"] == row["scored_count"] == 3
    ]
    by_raw = {row["raw_track_id"]: row for row in tail["directional_review_proposals"]}
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Cannot open source video")
    sheet = np.zeros((380 * len(selected), 1920, 3), dtype=np.uint8)
    records = []
    try:
        for index, row in enumerate(selected):
            raw_id = row["right_proposal_id"].split(":", 1)[1]
            track = by_raw[raw_id]
            points = track["observed_prefix_points"]
            nodes = [points[i] for i in (0, len(points) // 2, len(points) - 1)]
            records.append(
                {
                    "right_proposal_id": row["right_proposal_id"],
                    "source_times_s": [node["time_s"] for node in nodes],
                    "boxes": [node["bbox"] for node in nodes],
                }
            )
            for column, node in enumerate(nodes):
                cap.set(
                    cv2.CAP_PROP_POS_MSEC, (node["time_s"] - tail["source_time_offset_s"]) * 1000
                )
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise RuntimeError(f"Cannot decode {node['time_s']}")
                x, y, w, h = node["bbox"]
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 2)
                cv2.putText(
                    frame,
                    f"{raw_id} {node['time_s']:.1f}s",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )
                sheet[index * 380 : index * 380 + 360, column * 640 : (column + 1) * 640] = frame
    finally:
        cap.release()
    args.output_dir.mkdir(parents=True)
    image_path = args.output_dir / "three-positive-right-only.jpg"
    if not cv2.imwrite(str(image_path), sheet):
        raise RuntimeError("Cannot write source review sheet")
    manifest = {
        "status": "postscan_prediction_selected_source_sheet_not_independent_throw_labels",
        "source_sha256": tail["source_sha256"],
        "right_tail_sha256": digest(args.right_tail),
        "patches_sha256": digest(args.patches),
        "runner_sha256": digest(Path(__file__)),
        "selection": "right-only track with three scored and three positive frozen-model patches",
        "rows": records,
        "sheet": image_path.name,
        "sheet_sha256": digest(image_path),
        "limitations": [
            "Source review is targeted after model scoring and is not independent validation.",
            "Three frames establish the marked image object only, not exhaustive event truth.",
        ],
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"selected": len(records), "sheet": str(image_path)}))


if __name__ == "__main__":
    main()
