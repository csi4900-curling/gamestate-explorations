"""Render source frames for the upward lower-ice colour tracks in Latvia end 6."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark"
VIDEO = BASE / "canada-latvia-2024/source-360p.mp4"
PROBE = (
    BASE
    / "layout-router/full-2024-coverage/latvia24-full-v1/end6-lower-cap-direction-development.json"
)
OUT = BASE / "layout-router/full-2024-coverage/latvia24-full-v1"
TIMES = [6222, 6224, 6226, 6228, 6230, 6626, 6627, 6628, 6629]
SOURCE_REVIEW = {
    "D019": "player_clothing_at_tracked_pixel",
    "D020": "player_clothing_at_tracked_pixel",
    "D021": "player_clothing_at_tracked_pixel",
    "D028": "player_clothing_at_tracked_pixel",
}


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    probe = json.loads(PROBE.read_text())
    if probe["source_sha256"] != digest(VIDEO):
        raise ValueError("Source fingerprint differs")
    tracks = [row for row in probe["image_motion_tracks"] if row["direction"] == "upward"]
    if {row["diagnostic_track_id"] for row in tracks} != set(SOURCE_REVIEW):
        raise ValueError("Reviewed upward diagnostic tracks changed")
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    panels, evidence = [], []
    for time_s in TIMES:
        capture.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
        ok, frame = capture.read()
        if not ok:
            raise RuntimeError(f"Could not decode {time_s}")
        crop = frame[:, 320:].copy()
        annotations = []
        for track in tracks:
            nearest = min(track["points"], key=lambda point: abs(point["time_s"] - time_s))
            if abs(nearest["time_s"] - time_s) > 0.2:
                continue
            x, y, width, height = nearest["bbox"]
            cv2.rectangle(crop, (x - 320, y), (x + width - 320, y + height), (255, 0, 255), 2)
            cv2.putText(
                crop,
                track["diagnostic_track_id"],
                (x - 320, y - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                (0, 0, 0),
                1,
            )
            annotations.append(
                {"track_id": track["diagnostic_track_id"], "bbox_source_xywh_px": nearest["bbox"]}
            )
        canvas = np.full((390, 320, 3), 255, np.uint8)
        canvas[30:] = crop
        cv2.putText(canvas, str(time_s), (4, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
        panels.append(canvas)
        evidence.append({"source_time_s": time_s, "annotations": annotations})
    capture.release()
    sheet = np.vstack([np.hstack(panels[index : index + 3]) for index in (0, 3, 6)])
    image_path = OUT / "end6-upward-colour-source-review.jpg"
    if not cv2.imwrite(str(image_path), sheet):
        raise RuntimeError("Could not write contact sheet")
    result = {
        "status": "developer_source_pixel_review_not_independent_throw_labels",
        "source_sha256": probe["source_sha256"],
        "probe_sha256": digest(PROBE),
        "runner_sha256": digest(Path(__file__)),
        "image_sha256": digest(image_path),
        "upward_track_ids": [row["diagnostic_track_id"] for row in tracks],
        "same_agent_source_pixel_review": SOURCE_REVIEW,
        "physical_throw_verified": False,
        "frames": evidence,
    }
    (OUT / "end6-upward-colour-source-review.json").write_text(json.dumps(result, indent=2) + "\n")
    print(image_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
