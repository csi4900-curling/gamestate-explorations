"""Render selected periodic right-house cap changes against the source video."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark"
VIDEO = BASE / "canada-latvia-2024/source-360p.mp4"
OBSERVATIONS = BASE / "layout-router/full-2024-coverage/latvia24-full-v1/end6-periodic-right-board-development.json"
OUT = BASE / "layout-router/full-2024-coverage/latvia24-full-v1"
ANCHORS = (5900, 5910, 5920, 6330, 6340, 6550, 6560, 6570)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    observed = json.loads(OBSERVATIONS.read_text())
    if observed["source_sha256"] != digest(VIDEO):
        raise ValueError("Source fingerprint differs")
    by_anchor = {row["anchor_time_s"]: row for row in observed["windows"]}
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    panels, rows = [], []
    for anchor in ANCHORS:
        row = by_anchor[anchor]
        if row["observation_status"] != "partial_stable_colour_cap_proposals":
            raise ValueError(f"Selected source window no longer has cap proposals: {anchor}")
        time_s = anchor+2
        capture.set(cv2.CAP_PROP_POS_FRAMES, round(time_s*fps))
        ok, frame = capture.read()
        if not ok:
            raise RuntimeError(f"Could not decode {time_s}")
        crop = frame[:, 320:].copy()
        for cap in row["stable_cap_proposals"]:
            x, y = (round(v) for v in cap["pixel_center"])
            cv2.circle(crop, (x-320, y), 7, (255, 0, 255), 2)
            cv2.putText(crop, cap["local_observation_id"],
                        (x-320, y-9), cv2.FONT_HERSHEY_SIMPLEX,
                        0.36, (0, 0, 0), 1)
        canvas = np.full((390, 320, 3), 255, dtype=np.uint8)
        canvas[30:] = crop
        cv2.putText(canvas, str(time_s), (4, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
        panels.append(canvas)
        rows.append({"anchor_time_s": anchor,
                     "source_frame_time_s": time_s,
                     "stable_cap_proposals": row["stable_cap_proposals"]})
    capture.release()
    sheet = np.vstack([np.hstack(panels[index:index+2])
                       for index in (0, 2, 4, 6)])
    image_path = OUT / "end6-periodic-board-source-review.jpg"
    if not cv2.imwrite(str(image_path), sheet):
        raise RuntimeError("Could not write contact sheet")
    result = {
        "status": "selected_same_agent_source_review_not_board_or_throw_labels",
        "source_sha256": observed["source_sha256"],
        "observations_sha256": digest(OBSERVATIONS),
        "runner_sha256": digest(Path(__file__)),
        "image_sha256": digest(image_path),
        "frames": rows,
        "limitations": [
            "Frames are selected from prediction-visible image differences.",
            "Marked colour blobs are not verified stones or physical state changes.",
        ],
    }
    (OUT / "end6-periodic-board-source-review.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(image_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
