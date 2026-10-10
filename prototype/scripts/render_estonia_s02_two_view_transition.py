"""Source-only frames around Estonia S02's putative two-view overlap."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-estonia-2024"
VIDEO = BASE / "source-1080p-1650-2760.mp4"
RIGHT = (
    ROOT
    / "validation/throw-event-benchmark/layout-router/full-2024-coverage/yellow-bidirectional-motion-episodes-postscore.json"
)
LEFT = BASE / "left-bound-full-interval/s02-paired.json"
LEFT_RAW = BASE / "development-span-raw-v2.json"
TIMES = (1757.5, 1758.0, 1758.5, 1759.0, 1759.5, 1760.0)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    right = json.loads(RIGHT.read_text())
    left = json.loads(LEFT.read_text())
    left_raw = json.loads(LEFT_RAW.read_text())
    s02 = next(r for r in left_raw["events"] if r["id"] == "S02")
    if (
        left["source_sha256"] != digest(VIDEO)
        or left["candidate_id"] != s02["id"]
        or left["crossing_time_s"] != s02["crossing_time_s"]
        or right["rows"][2]["source"] != "estonia"
    ):
        raise ValueError("Source or Estonia episode changed")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    panels = []
    try:
        for t in TIMES:
            cap.set(cv2.CAP_PROP_POS_MSEC, (t - 1650) * 1000)
            ok, frame = cap.read()
            if not ok or frame.shape[:2] != (1080, 1920):
                raise RuntimeError(f"Could not decode {t}")
            view = cv2.resize(frame, (960, 540), interpolation=cv2.INTER_AREA)
            panel = np.full((574, 960, 3), (10, 20, 30), dtype=np.uint8)
            panel[34:, :] = view
            cv2.putText(
                panel,
                f"Estonia source {t:.1f}s",
                (8, 27),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.72,
                (255, 255, 255),
                2,
            )
            panels.append(panel)
    finally:
        cap.release()
    image_path = BASE / "yellow-s02-two-view-transition-source-review.jpg"
    if not cv2.imwrite(
        str(image_path),
        np.vstack([np.hstack(panels[:3]), np.hstack(panels[3:])]),
        [cv2.IMWRITE_JPEG_QUALITY, 92],
    ):
        raise RuntimeError("Could not write two-view sheet")
    manifest = {
        "status": "source_only_postscore_cross_view_overlap_review",
        "video_sha256": digest(VIDEO),
        "right_episode_sha256": digest(RIGHT),
        "left_candidate_sha256": digest(LEFT),
        "left_raw_other_resolution_sha256": digest(LEFT_RAW),
        "runner_sha256": digest(Path(__file__)),
        "image_sha256": digest(image_path),
        "source_times_s": TIMES,
        "s02_left_first_observed_s": s02["first_observed_s"],
        "s02_left_crossing_time_s": s02["crossing_time_s"],
        "same_agent_source_review": "pending_visual_inspection",
        "cross_view_physical_identity_verified": False,
    }
    (BASE / "yellow-s02-two-view-transition-source-review.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    print(image_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
