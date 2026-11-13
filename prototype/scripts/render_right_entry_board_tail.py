"""Render source-only later right-view frames after right-only entry proposals."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--fusion", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output already exists")
    fusion = json.loads(args.fusion.read_text())
    video_hash = digest(args.video)
    if fusion["source_sha256"] != video_hash:
        parser.error("Source fingerprints differ")
    rows = [
        row for row in fusion["right_entries"] if row["fusion_status"].startswith("right_only_")
    ]
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Unreadable video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
    sheets = []
    args.output_dir.mkdir(parents=True)
    try:
        for start in range(0, len(rows), 4):
            group = rows[start : start + 4]
            sheet = np.full((270 * len(group), 960, 3), 25, dtype=np.uint8)
            for i, row in enumerate(group):
                t0 = row["right_entry_time_s"]
                for col, delta in enumerate((15, 20, 25)):
                    t = t0 + delta
                    if t >= duration:
                        raise RuntimeError(f"Tail sample exceeds source: {t}")
                    cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
                    ok, frame = cap.read()
                    if not ok:
                        raise RuntimeError(f"Could not decode {t}")
                    crop = frame[120:360, 320:640]
                    top, left = 270 * i, 320 * col
                    sheet[top + 30 : top + 270, left : left + 320] = crop
                    cv2.putText(
                        sheet,
                        f"{row['right_raw_track_id']} +{delta}s {t:.1f}s",
                        (left + 5, top + 21),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.47,
                        (255, 255, 255),
                        1,
                        cv2.LINE_AA,
                    )
            path = args.output_dir / f"sheet-{start // 4 + 1:02}.jpg"
            if not cv2.imwrite(str(path), sheet):
                raise RuntimeError(f"Could not write {path}")
            sheets.append(
                {
                    "file": path.name,
                    "sha256": digest(path),
                    "right_track_ids": [row["right_raw_track_id"] for row in group],
                }
            )
    finally:
        cap.release()
    result = {
        "status": "source_only_right_tail_stills_not_stable_board_labels",
        "source_sha256": video_hash,
        "fusion_sha256": digest(args.fusion),
        "runner_sha256": digest(Path(__file__)),
        "reviewed_right_only_entry_count": len(rows),
        "sample_offsets_after_entry_s": [15, 20, 25],
        "sheets": sheets,
        "limitations": [
            "Sparse stills do not establish settle time or complete house occupancy.",
            "The fusion entries are development review proposals, not verified throws.",
        ],
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"entries": len(rows), "sheets": len(sheets)}))


if __name__ == "__main__":
    main()
