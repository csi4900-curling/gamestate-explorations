"""Render source-frame evidence for the S281 fourth-end shot-12 proposal."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
OUT = ROOT / "validation/official-shot-sequence"
IMAGE = OUT / "norway-e04-s12-source-contact-sheet.jpg"
MANIFEST = OUT / "norway-e04-s12-source-review-first.json"
TIMES = [3878.2, 3883.0, 3888.0, 3893.0, 3898.0, 3902.0]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if IMAGE.exists() or MANIFEST.exists():
        raise SystemExit("First S281 source-review artifacts already exist")
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise SystemExit("Cannot open source video")
    frames = []
    try:
        for time_s in TIMES:
            cap.set(cv2.CAP_PROP_POS_MSEC, time_s * 1000)
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Cannot read frame at {time_s}")
            frame = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
            cv2.putText(
                frame,
                f"{time_s:.1f} s",
                (8, 340),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (255, 255, 255),
                2,
            )
            frames.append(frame)
    finally:
        cap.release()
    sheet = np.vstack([np.hstack(frames[:3]), np.hstack(frames[3:])])
    if not cv2.imwrite(str(IMAGE), sheet, [cv2.IMWRITE_JPEG_QUALITY, 90]):
        raise RuntimeError("Could not save source contact sheet")
    result = {
        "status": "retrospective_source_video_review_not_independent_validation",
        "source_video_sha256": digest(VIDEO),
        "runner_sha256": digest(Path(__file__)),
        "frame_times_s": TIMES,
        "contact_sheet_sha256": digest(IMAGE),
        "candidate_camera_shot_id": "S281",
        "proposed_official_shot_id": "PREL001501-E04-S12",
        "source_observation": "Red-handled stone moves away from the Canadian wheelchair player while the delivery stick is in contact at sampled early frames; by 3898.0 s the stick is visibly separated. The fourth-end label is visible in the sampled frames.",
        "unverified": [
            "exact_release_time",
            "continuous_moving_stone_identity_across_camera_cut",
            "settled_board",
            "independent_event_annotation",
            "metric_trajectory",
        ],
    }
    MANIFEST.write_text(json.dumps(result, indent=2) + "\n")
    print(result["contact_sheet_sha256"])


if __name__ == "__main__":
    main()
