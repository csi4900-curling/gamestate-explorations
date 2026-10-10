"""Freeze the E028 source crop where a broom divides the red handle."""

from hashlib import sha256
import json
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
VIDEO = BASE / "source-1080p-full-format270.mp4"
PROBE = BASE / "full-reviewed-stone-fragment-merge-continuations-development.json"
OUT = BASE / "e028-fragment-source"
CROP = (675, 625, 825, 775)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("E028 fragment source packet already exists")
    probe = json.loads(PROBE.read_text())
    if digest(VIDEO) != probe["source_video_sha256"]:
        raise ValueError("Source video differs")
    row = next(item for item in probe["rows"] if item["episode_id"] == "E028")
    step = next(item for item in row["steps"] if item["source_time_s"] == 975.0)
    if (
        step["fragment_merge_count"] != 1
        or step["decision"]["status"] != "competing_caps_inside_motion_gate"
    ):
        raise ValueError("E028 source condition changed")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise ValueError("Video unreadable")
    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, step["decoded_frame_index"])
        ok, frame = cap.read()
        if not ok or frame.shape[:2] != (1080, 1920):
            raise ValueError("Source frame unreadable")
    finally:
        cap.release()
    OUT.mkdir(parents=True)
    x0, y0, x1, y1 = CROP
    path = OUT / "source-975.0-crop.png"
    if not cv2.imwrite(str(path), frame[y0:y1, x0:x1]):
        raise ValueError("Cannot write source crop")
    (OUT / "manifest.json").write_text(
        json.dumps(
            {
                "status": "unmarked_source_crop_for_agent_review_not_stone_identity_label",
                "source_video_sha256": probe["source_video_sha256"],
                "fragment_probe_sha256": digest(PROBE),
                "runner_sha256": digest(Path(__file__)),
                "episode_id": "E028",
                "source_time_s": 975.0,
                "decoded_frame_index": step["decoded_frame_index"],
                "crop_xyxy_px_1080": list(CROP),
                "file": path.name,
                "sha256": digest(path),
                "original_cap_component_boxes_px_1080": [
                    item["bbox_xywh_px_1080"] for item in step["original_components"]
                ],
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps({"file": path.name, "source_time_s": 975.0}))


if __name__ == "__main__":
    main()
