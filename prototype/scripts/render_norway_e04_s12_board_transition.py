"""Freeze post-cut source frames and official board counts for E04-S12."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
BOARDS = ROOT / "validation/official-shot-sequence/pwg2022-canada-norway-official-boards.json"
OUT = ROOT / "validation/official-shot-sequence"
IMAGE = OUT / "norway-e04-s12-board-transition-source-frames.jpg"
MANIFEST = OUT / "norway-e04-s12-board-transition-review-first.json"
TIMES = [3909.0, 3912.0, 3915.0, 3918.0, 3921.0]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if IMAGE.exists() or MANIFEST.exists():
        raise SystemExit("First board-transition review already exists")
    official = json.loads(BOARDS.read_text())
    fourth = next(end for end in official["ends"] if end["end"] == 4)
    prior, after = fourth["shots"][10:12]
    if (prior["official_shot_id"], after["official_shot_id"]) != (
            "PREL001501-E04-S11", "PREL001501-E04-S12"):
        raise SystemExit("Official diagram slots changed")
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise SystemExit("Cannot open source video")
    frames = []
    try:
        for time_s in TIMES:
            cap.set(cv2.CAP_PROP_POS_MSEC, 1000 * time_s)
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Cannot read frame at {time_s}")
            frame = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
            cv2.putText(frame, f"{time_s:.1f} s", (8, 340),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
            frames.append(frame)
    finally:
        cap.release()
    blank = np.zeros_like(frames[0])
    sheet = np.vstack([np.hstack(frames[:3]), np.hstack(frames[3:] + [blank])])
    if not cv2.imwrite(str(IMAGE), sheet, [cv2.IMWRITE_JPEG_QUALITY, 90]):
        raise RuntimeError("Could not save board-transition sheet")
    result = {
        "status": "retrospective_source_board_transition_review_not_independent_validation",
        "source_video_sha256": digest(VIDEO),
        "official_boards_sha256": digest(BOARDS),
        "runner_sha256": digest(Path(__file__)),
        "contact_sheet_sha256": digest(IMAGE),
        "frame_times_s": TIMES,
        "candidate_camera_shot_id": "S281",
        "receiving_camera_shot_id": "S282",
        "source_visual_observation": {
            "3909_s": "Red stone and yellow stone visible in the house as red approaches yellow.",
            "3912_s": "Yellow stone no longer visible in the house; red stone on right side.",
            "3918_to_3921_s": "One red stone appears stable on right side of the house; no yellow stone visible in the house.",
            "scope": "Visible house in sampled source frames only; stones elsewhere on the sheet are not inventoried.",
        },
        "official_diagrams": {
            "before": {"shot_id": prior["official_shot_id"],
                       "house_stone_counts": prior["stone_counts"],
                       "stones": prior["stones"]},
            "after": {"shot_id": after["official_shot_id"],
                      "house_stone_counts": after["stone_counts"],
                      "stones": after["stones"]},
        },
        "limitations": [
            "Matching board counts and layout support the sequence hypothesis but do not prove physical identity across the camera cut.",
            "The source observation is retrospective and not an independent blinded board label.",
            "No calibrated physical position, complete sheet board state, or exact settle time is inferred.",
        ],
    }
    MANIFEST.write_text(json.dumps(result, indent=2) + "\n")
    print(result["contact_sheet_sha256"])


if __name__ == "__main__":
    main()
