"""Render source-only frames for the longest provisional event gaps."""

import argparse
from hashlib import sha256
import json
from math import ceil
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
    parser.add_argument("--union", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists")
    union = json.loads(args.union.read_text())
    video_hash = digest(args.video)
    if video_hash != union["source_sha256"]:
        parser.error("Source fingerprints differ")
    selected = [row for row in union["raw_candidates"] if row["tier"] in (
        "screen_provisional", "pre_split_review_only")]
    gaps = sorted(zip(selected, selected[1:]),
                  key=lambda pair: pair[1]["passage_time_s"] -
                  pair[0]["passage_time_s"], reverse=True)[:5]
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    args.output_dir.mkdir(parents=True)
    rows = []
    try:
        for index, (before, after) in enumerate(gaps, 1):
            low, high = before["passage_time_s"], after["passage_time_s"]
            times = list(range(ceil(low / 15) * 15, int(high), 15))
            tiles = []
            frames = []
            for second in times:
                frame_index = round(second * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise RuntimeError(f"Cannot decode source second {second}")
                tile = cv2.resize(frame, (480, 270))
                cv2.rectangle(tile, (0, 0), (100, 27), (0, 0, 0), -1)
                cv2.putText(tile, str(second), (8, 19),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                tiles.append(tile)
                frames.append({"source_time_s": second,
                               "decoded_frame_index": frame_index})
            if not tiles:
                raise ValueError("Gap has no sampled interior")
            while len(tiles) % 3:
                tiles.append(np.zeros_like(tiles[0]))
            sheet = np.vstack([np.hstack(tiles[i:i + 3])
                               for i in range(0, len(tiles), 3)])
            name = f"gap-{index:02d}-{before['candidate_id']}-{after['candidate_id']}.jpg"
            path = args.output_dir / name
            if not cv2.imwrite(str(path), sheet):
                raise RuntimeError(f"Cannot write {path}")
            intervening = [row for row in union["raw_candidates"]
                           if low < row["passage_time_s"] < high]
            rows.append({"rank": index,
                         "before_candidate_id": before["candidate_id"],
                         "after_candidate_id": after["candidate_id"],
                         "interval_s": [low, high],
                         "duration_s": round(high - low, 3),
                         "intervening_raw_candidate_ids": [
                             row["candidate_id"] for row in intervening],
                         "frames": frames,
                         "sheet": name,
                         "sheet_sha256": digest(path),
                         "physical_throws_in_gap_verified": False})
    finally:
        cap.release()
    manifest = {
        "status": "sparse_source_review_of_longest_candidate_gaps_not_exhaustive_throw_labels",
        "source_sha256": video_hash,
        "union_sha256": digest(args.union),
        "runner_sha256": digest(Path(__file__)),
        "sample_period_s": 15,
        "gap_selection": "Five longest adjacent gaps among screen-provisional and pre-split-review rows",
        "gaps": rows,
        "limitations": [
            "Fifteen-second stills can miss a full stone traverse between samples.",
            "Candidates can be false or duplicated, so intervals are not physical inter-throw gaps.",
            "Raw intervening candidates are retained but not promoted by this audit.",
        ],
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"gaps": len(rows),
                      "sampled_frames": sum(len(row["frames"]) for row in rows)}))


if __name__ == "__main__":
    main()
