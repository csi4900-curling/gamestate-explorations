"""Render source frames for the fixed Slovakia yellow transfer interval."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-slovakia-2024"
VIDEO = BASE / "source-1080p-1650-2760.mp4"
AUDIT = BASE / "yellow-handoff-1990-2070-development.json"
TIMES = (2034, 2036, 2038, 2041, 2044, 2046)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    audit = json.loads(AUDIT.read_text())
    if audit["target_video_sha256"] != digest(VIDEO):
        raise ValueError("Transfer video changed")
    paths = [p for p in audit["body_image_paths"] if p["direction"] == "upward"]
    if len(paths) != 1:
        raise ValueError("Expected one upward path")
    by_time = {p["time_s"]: p for p in paths[0]["points"]}
    if any(t not in by_time for t in TIMES):
        raise ValueError("Selected source time not in path")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    panels = []
    try:
        for t in TIMES:
            cap.set(cv2.CAP_PROP_POS_MSEC, (t - 1650) * 1000)
            ok, frame = cap.read()
            if not ok or frame.shape[:2] != (1080, 1920):
                raise RuntimeError(f"Could not decode {t}")
            view = cv2.resize(frame[:, 960:], (480, 540), interpolation=cv2.INTER_AREA)
            x, y = by_time[t]["center_1080p_px"]
            x, y = round((x - 960) / 2), round(y / 2)
            cv2.rectangle(view, (x - 20, y - 13), (x + 20, y + 13), (255, 0, 255), 2)
            cv2.rectangle(view, (0, 0), (480, 38), (10, 20, 30), -1)
            cv2.putText(
                view,
                f"{t}s yellow body path",
                (8, 27),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.62,
                (255, 255, 255),
                2,
            )
            panels.append(view)
    finally:
        cap.release()
    image_path = BASE / "yellow-handoff-1990-2070-source-review.jpg"
    if not cv2.imwrite(
        str(image_path),
        np.vstack([np.hstack(panels[:3]), np.hstack(panels[3:])]),
        [cv2.IMWRITE_JPEG_QUALITY, 90],
    ):
        raise RuntimeError("Could not write sheet")
    manifest = {
        "status": "same_agent_source_review_of_fixed_cross_recording_transfer",
        "audit_sha256": digest(AUDIT),
        "video_sha256": digest(VIDEO),
        "runner_sha256": digest(Path(__file__)),
        "image_sha256": digest(image_path),
        "source_times_s": TIMES,
        "same_agent_source_review": "boxes_follow_one_visible_moving_yellow_stone",
        "physical_throw_identity_independently_verified": False,
        "physical_stop_verified": False,
    }
    (BASE / "yellow-handoff-1990-2070-source-review.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    print(image_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
