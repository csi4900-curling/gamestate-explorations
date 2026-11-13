"""Render all upward high-resolution Latvia end-6 colour paths for source review."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark"
VIDEO = BASE / "canada-latvia-2024/source-1080p-5670-6670.mp4"
PROBE = (
    BASE
    / "layout-router/full-2024-coverage/latvia24-full-v1/end6-highres-cap-transfer-development.json"
)
OUT = BASE / "layout-router/full-2024-coverage/latvia24-full-v1"
SOURCE_REVIEW = {
    "D021": "person_or_broom_pixels_at_tracked_locations",
    "D022": "player_clothing_at_tracked_locations",
    "D023": "player_head_or_clothing_at_tracked_locations",
    "D025": "player_clothing_at_tracked_locations",
    "D026": "player_clothing_or_wheelchair_at_tracked_locations",
}


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def panel(frame, track_id, point):
    x, y, width, height = point["bbox_1080p"]
    center = (x + width // 2, y + height // 2)
    right = cv2.resize(frame[:, 960:], (320, 360), interpolation=cv2.INTER_AREA)
    cv2.rectangle(
        right,
        (round(x / 3 - 320), round(y / 3)),
        (round((x + width) / 3 - 320), round((y + height) / 3)),
        (255, 0, 255),
        2,
    )
    expanded = cv2.copyMakeBorder(
        frame, 100, 100, 100, 100, cv2.BORDER_CONSTANT, value=(245, 245, 245)
    )
    close = cv2.getRectSubPix(expanded, (160, 160), (center[0] + 100, center[1] + 100))
    cx, cy = 80 - width // 2, 80 - height // 2
    cv2.rectangle(close, (cx, cy), (cx + width, cy + height), (255, 0, 255), 2)
    canvas = np.full((390, 480, 3), 245, np.uint8)
    canvas[30:, :320] = right
    canvas[110:270, 320:] = close
    cv2.putText(
        canvas,
        f"{track_id} {point['time_s']}s",
        (8, 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 0, 0),
        1,
    )
    return canvas


def main():
    probe = json.loads(PROBE.read_text())
    if probe["high_video_sha256"] != digest(VIDEO):
        raise ValueError("Source differs from high-resolution probe")
    tracks = [row for row in probe["image_motion_tracks"] if row["direction"] == "upward"]
    if not tracks:
        raise ValueError("No upward paths to review")
    if {row["diagnostic_track_id"] for row in tracks} != set(SOURCE_REVIEW):
        raise ValueError("Upward paths changed; source review must be repeated")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    rows, manifest_rows = [], []
    try:
        for track in tracks:
            points = track["points"]
            selected = [points[0], points[len(points) // 2], points[-1]]
            panels = []
            for point in selected:
                cap.set(cv2.CAP_PROP_POS_MSEC, (point["time_s"] - 5670) * 1000)
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f"Could not decode {point['time_s']}")
                panels.append(panel(frame, track["diagnostic_track_id"], point))
            rows.append(np.hstack(panels))
            manifest_rows.append(
                {
                    "track_id": track["diagnostic_track_id"],
                    "selected_times_s": [p["time_s"] for p in selected],
                    "high_only_point_count": sum(not p["matched_360p_within_5px"] for p in points),
                    "point_count": len(points),
                }
            )
    finally:
        cap.release()
    image_path = OUT / "end6-highres-upward-source-review.jpg"
    if not cv2.imwrite(str(image_path), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90]):
        raise RuntimeError("Could not write source sheet")
    result = {
        "status": "prediction_selected_highres_source_review_not_independent_event_labels",
        "probe_sha256": digest(PROBE),
        "video_sha256": digest(VIDEO),
        "runner_sha256": digest(Path(__file__)),
        "image_sha256": digest(image_path),
        "tracks": manifest_rows,
        "same_agent_source_pixel_review": SOURCE_REVIEW,
        "physical_throw_verified": False,
    }
    (OUT / "end6-highres-upward-source-review.json").write_text(json.dumps(result, indent=2) + "\n")
    print(image_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
