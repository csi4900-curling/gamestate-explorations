"""Review every phase of Estonia's first yellow body path, including its end."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-estonia-2024"
VIDEO = BASE / "source-1080p-1650-2760.mp4"
TRANSFER = BASE / "yellow-contour-1720-1800-first-transfer.json"
TIMES = (1738, 1753, 1754, 1755, 1756, 1757, 1758, 1759)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    transfer = json.loads(TRANSFER.read_text())
    if transfer["target_video_sha256"] != digest(VIDEO):
        raise ValueError("Estonia source changed")
    paths = transfer["body_image_paths"]
    if len(paths) != 1:
        raise ValueError("Expected one body path")
    by_time = {p["time_s"]: p for p in paths[0]["points"]}
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    panels = []
    try:
        for t in TIMES:
            cap.set(cv2.CAP_PROP_POS_MSEC, (t - 1650) * 1000)
            ok, frame = cap.read()
            if not ok or frame.shape[:2] != (1080, 1920):
                raise RuntimeError(f"Could not decode {t}")
            view = cv2.resize(frame[:, 960:], (480, 540), interpolation=cv2.INTER_AREA)
            if t in by_time:
                x, y = by_time[t]["center_1080p_px"]
                x, y = round((x - 960) / 2), round(y / 2)
                cv2.rectangle(view, (x - 20, y - 13), (x + 20, y + 13), (255, 0, 255), 2)
            cv2.rectangle(view, (0, 0), (480, 38), (10, 20, 30), -1)
            label = f"{t}s {'body match' if t in by_time else 'no body match'}"
            cv2.putText(view, label, (8, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2)
            panels.append(view)
    finally:
        cap.release()
    image_path = BASE / "yellow-contour-1720-1800-first-source-review.jpg"
    if not cv2.imwrite(
        str(image_path),
        np.vstack([np.hstack(panels[:4]), np.hstack(panels[4:])]),
        [cv2.IMWRITE_JPEG_QUALITY, 90],
    ):
        raise RuntimeError("Could not write source review")
    manifest = {
        "status": "same_agent_postresult_direction_source_review",
        "transfer_sha256": digest(TRANSFER),
        "video_sha256": digest(VIDEO),
        "runner_sha256": digest(Path(__file__)),
        "image_sha256": digest(image_path),
        "source_times_s": TIMES,
        "same_agent_source_review": "pending_visual_inspection",
        "physical_throw_identity_independently_verified": False,
    }
    (BASE / "yellow-contour-1720-1800-first-source-review.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    print(image_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
