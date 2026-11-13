"""Render source frames around selected full-match displayed-end changes."""

import argparse
from hashlib import sha256
import json
from math import ceil, floor
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
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--union-with-display", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists")
    joined = json.loads(args.union_with_display.read_text())
    source_hash = digest(args.video)
    if source_hash != joined["source_sha256"]:
        parser.error("Source fingerprints differ")
    targets = [
        row
        for row in joined["raw_candidates"]
        if row["tier"] == "screen_provisional"
        and row["broadcast_display_context"]["display_context_status"] == "bracketed_display_change"
    ]
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    args.output_dir.mkdir(parents=True)
    rows = []
    try:
        for target in targets:
            t = target["passage_time_s"]
            start = floor((t - 16) / 2) * 2
            stop = ceil((t + 16) / 2) * 2
            tiles, frames = [], []
            for second in range(start, stop + 1, 2):
                frame_index = round(second * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise RuntimeError(f"Cannot decode source second {second}")
                tile = cv2.resize(frame, (480, 270))
                cv2.rectangle(tile, (0, 0), (100, 26), (0, 0, 0), -1)
                cv2.putText(
                    tile, str(second), (8, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1
                )
                tiles.append(tile)
                frames.append({"source_time_s": second, "decoded_frame_index": frame_index})
            while len(tiles) % 3:
                tiles.append(np.zeros_like(tiles[0]))
            sheet = np.vstack([np.hstack(tiles[i : i + 3]) for i in range(0, len(tiles), 3)])
            name = target["candidate_id"].lower() + "-display-change.jpg"
            path = args.output_dir / name
            if not cv2.imwrite(str(path), sheet):
                raise RuntimeError(f"Cannot write {path}")
            rows.append(
                {
                    "candidate_id": target["candidate_id"],
                    "passage_time_s": t,
                    "colour_claim": target["colour_claim"],
                    "left_marker": target["broadcast_display_context"]["left_marker"],
                    "right_marker": target["broadcast_display_context"]["right_marker"],
                    "frames": frames,
                    "sheet": name,
                    "sheet_sha256": digest(path),
                    "physical_end_identity_verified": False,
                }
            )
    finally:
        cap.release()
    output = {
        "status": "source_frames_at_display_change_not_physical_end_assignment",
        "source_sha256": source_hash,
        "union_with_display_sha256": digest(args.union_with_display),
        "runner_sha256": digest(Path(__file__)),
        "sample_step_s": 2,
        "review_target_count": len(rows),
        "targets": rows,
        "limitations": [
            "Two-second stills and split-screen broadcast views cannot prove complete sheet emptiness.",
            "The delayed displayed-end change is not an exact physical end boundary.",
            "Candidate physical throw identity and end membership remain unverified.",
        ],
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {"targets": len(rows), "sampled_frames": sum(len(row["frames"]) for row in rows)}
        )
    )


if __name__ == "__main__":
    main()
