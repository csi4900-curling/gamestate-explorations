"""Render both camera panels around right entries whose left lookback is unsupported."""

import argparse
from hashlib import sha256
import json
from math import ceil, floor
from pathlib import Path

import cv2
import numpy as np


def digest(path):
    value = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--fusion", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists")
    fusion = json.loads(args.fusion.read_text())
    source_hash = digest(args.video)
    if fusion["source_sha256"] != source_hash:
        parser.error("Source fingerprints differ")
    selected = [row for row in fusion["right_entries"] if row["fusion_status"] ==
                "right_only_prior_left_coverage_gap_review"]
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    args.output_dir.mkdir(parents=True)
    rows = []
    try:
        for entry in selected:
            t = entry["right_entry_time_s"]
            start = floor((t - 20) / 2) * 2
            stop = ceil((t + 8) / 2) * 2
            frames, tiles = [], []
            for second in range(start, stop + 1, 2):
                frame_index = round(second * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise RuntimeError(f"Cannot decode source second {second}")
                cv2.rectangle(frame, (0, 0), (100, 27), (0, 0, 0), -1)
                cv2.putText(frame, str(second), (8, 19),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                tiles.append(frame)
                frames.append({"source_time_s": second,
                               "decoded_frame_index": frame_index})
            while len(tiles) % 2:
                tiles.append(np.zeros_like(tiles[0]))
            sheet = np.vstack([np.hstack(tiles[i:i + 2])
                               for i in range(0, len(tiles), 2)])
            name = entry["right_raw_track_id"].lower() + "-lookback-gap.jpg"
            path = args.output_dir / name
            if not cv2.imwrite(str(path), sheet):
                raise RuntimeError(f"Cannot write {path}")
            rows.append({"right_raw_track_id": entry["right_raw_track_id"],
                         "right_entry_time_s": t,
                         "colour_claim": entry["right_colour_claim"],
                         "left_coverage_status_at_right_entry":
                         entry["left_coverage_status"],
                         "frames": frames,
                         "sheet": name, "sheet_sha256": digest(path),
                         "physical_cross_view_identity_verified": False})
    finally:
        cap.release()
    manifest = {
        "status": "source_review_of_prior_left_coverage_gap_not_throw_labels",
        "source_sha256": source_hash,
        "fusion_sha256": digest(args.fusion),
        "runner_sha256": digest(Path(__file__)),
        "sample_step_s": 2,
        "rows": rows,
        "limitations": [
            "Two-second frames can miss the exact physical release or camera handoff.",
            "Chronological same-colour source motion does not verify one physical stone across views.",
        ],
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"entries": len(rows),
                      "sampled_frames": sum(len(row["frames"]) for row in rows)}))


if __name__ == "__main__":
    main()
