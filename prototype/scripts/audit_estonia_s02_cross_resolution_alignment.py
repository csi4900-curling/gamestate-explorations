"""Check 360p full-source to 1080p excerpt frame alignment at S02."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-estonia-2024"
FULL = BASE / "source.mp4"
EXCERPT = BASE / "source-1080p-1650-2760.mp4"
OUTPUT = BASE / "yellow-s02-cross-resolution-alignment-postreview.json"
CHECKPOINTS_S = (1759.5, 1779.5)
EXCERPT_OFFSET_S = 1650
SEARCH_FRAME_OFFSETS = range(-30, 31)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def gray_frame(cap, frame_index):
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, frame = cap.read()
    if not ok:
        raise RuntimeError(f"Cannot decode frame {frame_index}")
    return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


def main():
    full = cv2.VideoCapture(str(FULL), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    excerpt = cv2.VideoCapture(str(EXCERPT), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if (
        not full.isOpened()
        or not excerpt.isOpened()
        or full.get(cv2.CAP_PROP_FPS) != 30
        or excerpt.get(cv2.CAP_PROP_FPS) != 30
    ):
        raise RuntimeError("Expected two 30-fps source files")
    results = []
    try:
        for t in CHECKPOINTS_S:
            target = gray_frame(excerpt, round((t - EXCERPT_OFFSET_S) * 30))
            if target.shape != (1080, 1920):
                raise ValueError("High-resolution excerpt dimensions changed")
            target = cv2.resize(target, (640, 360), interpolation=cv2.INTER_AREA).astype(np.float32)
            candidates = []
            for offset in SEARCH_FRAME_OFFSETS:
                observed = gray_frame(full, round(t * 30) + offset)
                if observed.shape != (360, 640):
                    raise ValueError("Full-source dimensions changed")
                mae = float(np.mean(np.abs(target - observed.astype(np.float32))))
                candidates.append(
                    {"offset_frames": offset, "mean_absolute_gray_difference": round(mae, 4)}
                )
            ordered = sorted(candidates, key=lambda row: row["mean_absolute_gray_difference"])
            results.append(
                {
                    "source_time_s": t,
                    "best": ordered[0],
                    "second_best": ordered[1],
                    "zero_offset": next(row for row in candidates if row["offset_frames"] == 0),
                }
            )
    finally:
        full.release()
        excerpt.release()
    output = {
        "status": "postreview_two_checkpoint_cross_resolution_alignment_not_global_sync_proof",
        "full_source_sha256": digest(FULL),
        "excerpt_sha256": digest(EXCERPT),
        "runner_sha256": digest(Path(__file__)),
        "full_source_frame_size": [640, 360],
        "excerpt_frame_size": [1920, 1080],
        "excerpt_source_offset_s": EXCERPT_OFFSET_S,
        "search_offsets_frames": [-30, 30],
        "checkpoints": results,
        "zero_offset_best_at_all_checkpoints": all(
            row["best"]["offset_frames"] == 0 for row in results
        ),
        "limitations": [
            "Only two checkpoints near the selected event and post-event board are tested.",
            "Similar decoded frames support timeline correspondence, not physical object identity.",
            "Other times in the full source may have separate edit or sync behavior.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps([(r["source_time_s"], r["best"]) for r in results]))


if __name__ == "__main__":
    main()
