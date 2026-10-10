"""Render simultaneous right-exit/left-entry crops for Estonia S02."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-estonia-2024"
VIDEO = BASE / "source-1080p-1650-2760.mp4"
RIGHT = ROOT / "validation/throw-event-benchmark/layout-router/full-2024-coverage/yellow-bidirectional-motion-episodes-postscore.json"
LEFT = BASE / "left-bound-full-interval/s02-paired.json"
TIMES = (1757.5, 1758.0, 1758.5, 1759.0, 1759.5, 1760.0)
LEFT_CROP_XYXY = (280, 0, 720, 300)
RIGHT_CROP_XYXY = (1160, 780, 1600, 1080)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    left = json.loads(LEFT.read_text())
    if left["candidate_id"] != "S02" or left["source_sha256"] != digest(VIDEO):
        raise ValueError("S02 source changed")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    pairs = []
    try:
        for t in TIMES:
            cap.set(cv2.CAP_PROP_POS_MSEC, (t-1650)*1000)
            ok, frame = cap.read()
            if not ok or frame.shape[:2] != (1080, 1920):
                raise RuntimeError(f"Could not decode {t}")
            panels = []
            for label, (x1, y1, x2, y2) in (
                    ("left entry", LEFT_CROP_XYXY),
                    ("right exit", RIGHT_CROP_XYXY)):
                view = frame[y1:y2, x1:x2].copy()
                panel = np.full((334, 440, 3), (10, 20, 30), dtype=np.uint8)
                panel[34:, :] = view
                cv2.putText(panel, f"{t:.1f}s {label}", (6, 24),
                            cv2.FONT_HERSHEY_SIMPLEX, .64, (255, 255, 255), 2)
                panels.append(panel)
            pairs.append(np.hstack(panels))
    finally:
        cap.release()
    image_path = BASE / "yellow-s02-simultaneous-edge-overlap.jpg"
    if not cv2.imwrite(str(image_path), np.vstack(pairs),
                       [cv2.IMWRITE_JPEG_QUALITY, 94]):
        raise RuntimeError("Could not write edge overlap sheet")
    manifest = {
        "status": "same_agent_source_only_two_view_edge_overlap_review",
        "video_sha256": digest(VIDEO),
        "right_episode_sha256": digest(RIGHT),
        "left_candidate_sha256": digest(LEFT),
        "runner_sha256": digest(Path(__file__)),
        "image_sha256": digest(image_path),
        "source_times_s": TIMES,
        "left_crop_xyxy_1080p": LEFT_CROP_XYXY,
        "right_crop_xyxy_1080p": RIGHT_CROP_XYXY,
        "same_agent_source_review": "pending_visual_inspection",
        "physical_same_stone_identity_independently_verified": False,
    }
    (BASE / "yellow-s02-simultaneous-edge-overlap.json").write_text(
        json.dumps(manifest, indent=2) + "\n")
    print(image_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
