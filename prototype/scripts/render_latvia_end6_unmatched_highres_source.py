"""Render source-backed crops for three unmatched Latvia high-res red paths."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from right_motion_onset import observed_quiet_to_motion  # noqa: E402

BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
VIDEO = BASE / "source-1080p-5670-6670.mp4"
RED = (
    ROOT
    / "validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1/end6-highres-red-full-transfer-development.json"
)
JOIN = BASE / "end6-cross-resolution-body-cap-development.json"
ONSET = BASE / "end6-highres-body-onset-crosscheck-development.json"
IMAGE = BASE / "end6-unmatched-highres-red-source.jpg"
MANIFEST = BASE / "end6-unmatched-highres-red-source.json"
IDS = ("B005", "B006", "B007")


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if IMAGE.exists() or MANIFEST.exists():
        raise ValueError("Source packet already exists")
    red, join, onset = (json.loads(p.read_text()) for p in (RED, JOIN, ONSET))
    source_hash = digest(VIDEO)
    if (
        source_hash != red["source_video_sha256"]
        or source_hash != join["highres_source_sha256"]
        or source_hash != onset["source_video_sha256"]
        or join["unmatched_highres_path_ids"]["red"] != list(IDS)
    ):
        raise ValueError("Unmatched-path source lineage differs")
    paths = {p["diagnostic_path_id"]: p for p in red["red_supported_image_paths"]}
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        raise ValueError("Source unreadable")
    fps = capture.get(cv2.CAP_PROP_FPS)
    bands = []
    rows = []
    try:
        for path_id in IDS:
            path = paths[path_id]
            crops = []
            point_rows = []
            for point in path["points"]:
                time_s = point["time_s"]
                frame_index = round((time_s - 5670) * fps)
                capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                ok, frame = capture.read()
                if not ok or frame.shape[:2] != (1080, 1920):
                    raise ValueError(f"Frame {frame_index} unreadable")
                x, y = point["center_1080p_px"]
                x0, y0 = max(0, x - 130), max(0, y - 110)
                x1, y1 = min(1920, x + 130), min(1080, y + 110)
                crop = frame[y0:y1, x0:x1].copy()
                cv2.circle(crop, (x - x0, y - y0), 10, (0, 255, 0), 2)
                cv2.putText(
                    crop,
                    f"{path_id} {time_s}",
                    (7, 23),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 0, 255),
                    2,
                )
                crop = cv2.copyMakeBorder(
                    crop,
                    0,
                    220 - crop.shape[0],
                    0,
                    260 - crop.shape[1],
                    cv2.BORDER_CONSTANT,
                    value=(0, 0, 0),
                )
                crops.append(crop)
                point_rows.append(
                    {
                        "source_time_s": time_s,
                        "decoded_frame_index": frame_index,
                        "marked_center_1080p": [x, y],
                        "crop_xyxy_1080p": [x0, y0, x1, y1],
                    }
                )
            if len(crops) != 3:
                raise ValueError("Expected three source points per path")
            bands.append(cv2.hconcat(crops))
            normalized = [
                {"time_s": p["time_s"], "pixel": [value * 2 / 3 for value in p["center_1080p_px"]]}
                for p in path["points"]
            ]
            onset_status = observed_quiet_to_motion(
                normalized, "positive_y", quiet_rate_px_s=6, strong_rate_px_s=24
            )["status"]
            rows.append(
                {
                    "highres_path_id": path_id,
                    "reviewed_marked_pixel_class": (
                        "red_clothing" if path_id == "B005" else "face_or_head"
                    ),
                    "review_type": "same_agent_source_visual_inspection",
                    "onset_status": onset_status,
                    "points": point_rows,
                }
            )
    finally:
        capture.release()
    if not cv2.imwrite(str(IMAGE), cv2.vconcat(bands)):
        raise ValueError("Could not write source packet")
    payload = {
        "status": "same_agent_unmatched_path_source_pixel_review_not_throw_truth",
        "source_video_sha256": source_hash,
        "red_path_sha256": digest(RED),
        "cross_resolution_join_sha256": digest(JOIN),
        "onset_crosscheck_sha256": digest(ONSET),
        "onset_code_sha256": digest(ROOT / "prototype/right_motion_onset.py"),
        "runner_sha256": digest(Path(__file__)),
        "contact_sheet": IMAGE.name,
        "contact_sheet_sha256": digest(IMAGE),
        "rows": rows,
        "limitations": [
            "Classes are same-agent visual readings of the marked source pixels, not independent physical throw labels.",
            "Insufficient onset observations is a timing abstention, not an appearance classification.",
        ],
    }
    MANIFEST.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"paths": len(rows), "onset_statuses": [r["onset_status"] for r in rows]}))


if __name__ == "__main__":
    main()
