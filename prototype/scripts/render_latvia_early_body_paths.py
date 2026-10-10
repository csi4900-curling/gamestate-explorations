"""Render every upward path from the frozen early 1080p Latvia transfer."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark"
VIDEO = BASE / "canada-latvia-2024/source-1080p-1650-2760.mp4"
TRANSFER = (
    BASE
    / "layout-router/full-2024-coverage/latvia24-full-v1/early-highres-body-handle-transfer-development.json"
)
OUT = BASE / "layout-router/full-2024-coverage/latvia24-full-v1"
SOURCE_REVIEW = {
    "B003": "source_visible_moving_yellow_stone",
    "B004": "source_visible_moving_yellow_stone",
    "B005": "source_visible_moving_yellow_stone_template_source_event",
    "B006": "source_visible_moving_yellow_stone",
    "B007": "source_visible_moving_yellow_stone",
}


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    transfer = json.loads(TRANSFER.read_text())
    if transfer["source_video_sha256"] != digest(VIDEO):
        raise ValueError("Source differs from transfer")
    paths = [row for row in transfer["supported_image_paths"] if row["direction"] == "upward"]
    if not paths:
        raise ValueError("No upward source paths")
    if {row["diagnostic_path_id"] for row in paths} != set(SOURCE_REVIEW):
        raise ValueError("Upward paths changed; source review must be repeated")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    rows, manifest = [], []
    try:
        for path in paths:
            points = path["points"]
            selected = [points[0], points[len(points) // 2], points[-1]]
            panels = []
            for point in selected:
                time_s = point["time_s"]
                cap.set(cv2.CAP_PROP_POS_MSEC, (time_s - 1650) * 1000)
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f"Cannot decode {time_s}")
                view = cv2.resize(frame[:, 960:], (480, 540), interpolation=cv2.INTER_AREA)
                x, y = point["center_1080p_px"]
                x = round((x - 960) / 2)
                y = round(y / 2)
                cv2.rectangle(view, (x - 24, y - 18), (x + 24, y + 18), (255, 0, 255), 2)
                cv2.rectangle(view, (0, 0), (480, 38), (10, 20, 30), -1)
                cv2.putText(
                    view,
                    f"{path['diagnostic_path_id']} {time_s}s",
                    (8, 27),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    (255, 255, 255),
                    2,
                )
                panels.append(view)
            rows.append(np.hstack(panels))
            manifest.append(
                {
                    "path_id": path["diagnostic_path_id"],
                    "selected_times_s": [p["time_s"] for p in selected],
                    "full_path_interval_s": [path["first_observed_s"], path["last_observed_s"]],
                }
            )
    finally:
        cap.release()
    image_path = OUT / "early-highres-body-upward-source-review.jpg"
    if not cv2.imwrite(str(image_path), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90]):
        raise RuntimeError("Could not write source review")
    result = {
        "status": "prediction_selected_upward_source_sheet_not_independent_validation",
        "transfer_sha256": digest(TRANSFER),
        "video_sha256": digest(VIDEO),
        "runner_sha256": digest(Path(__file__)),
        "image_sha256": digest(image_path),
        "paths": manifest,
        "same_agent_source_review": SOURCE_REVIEW,
        "independent_event_labels": False,
    }
    (OUT / "early-highres-body-upward-source-review.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(image_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
