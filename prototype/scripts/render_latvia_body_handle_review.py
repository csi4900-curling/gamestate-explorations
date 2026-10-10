"""Source sheet contrasting a moving stone with the B006 wheelchair alias."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark"
POSITIVE = BASE / "canada-latvia-2024/source-1080p-1650-2760.mp4"
BLIND = BASE / "canada-latvia-2024/source-1080p-5670-6670.mp4"
SCREEN = BASE / "layout-router/full-2024-coverage/latvia24-full-v1/end6-highres-body-handle-screen-development.json"
BODY = BASE / "layout-router/full-2024-coverage/latvia24-full-v1/end6-highres-body-template-development.json"
OUT = BASE / "layout-router/full-2024-coverage/latvia24-full-v1"
POSITIVE_TIMES = (2309, 2311, 2313, 2315)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def render(capture, clip_start, time_s, point, title):
    capture.set(cv2.CAP_PROP_POS_MSEC, (time_s-clip_start)*1000)
    ok, frame = capture.read()
    if not ok:
        raise RuntimeError(f"Cannot decode {time_s}")
    view = cv2.resize(frame[:, 960:], (480, 540), interpolation=cv2.INTER_AREA)
    x, y = point["center_1080p_px"]
    x = round((x-960)/2)
    y = round(y/2)
    cv2.rectangle(view, (x-24, y-18), (x+24, y+18), (255, 0, 255), 2)
    cv2.rectangle(view, (0, 0), (480, 42), (10, 20, 30), -1)
    cv2.putText(view, title, (8, 29), cv2.FONT_HERSHEY_SIMPLEX,
                .65, (255, 255, 255), 2)
    return view


def main():
    body = json.loads(BODY.read_text())
    screen = json.loads(SCREEN.read_text())
    if screen["body_probe_sha256"] != digest(BODY):
        raise ValueError("Body probe changed")
    if screen["positive_video_sha256"] != digest(POSITIVE) or \
            screen["blind_video_sha256"] != digest(BLIND):
        raise ValueError("Video source changed")
    positive_rows = {r["time_s"]: r for r in screen["positive_control"]}
    false_path = next(p for p in body["supported_image_paths"]
                      if p["diagnostic_path_id"] == "B006")
    false_points = {p["time_s"]: p for p in false_path["points"]}
    blind_rows = {r["time_s"]: r for r in screen["blind_samples_with_body_proposals"]}
    positive_cap = cv2.VideoCapture(str(POSITIVE), cv2.CAP_FFMPEG,
                                    [cv2.CAP_PROP_N_THREADS, 1])
    blind_cap = cv2.VideoCapture(str(BLIND), cv2.CAP_FFMPEG,
                                 [cv2.CAP_PROP_N_THREADS, 1])
    panels = []
    try:
        for t in POSITIVE_TIMES:
            point = max(positive_rows[t]["body_proposals"], key=lambda p: p["score"])
            pixels = point["handle_colour_pixels"]["yellow"]
            panels.append(render(positive_cap, 1650, t, point,
                                 f"stone {t}s  yellow={pixels}"))
        for t in (6229, 6230, 6231, 6232):
            body_point = false_points[t]
            point = next(p for p in blind_rows[t]["body_proposals"]
                         if p["center_1080p_px"] == body_point["center_1080p_px"])
            pixels = max(point["handle_colour_pixels"].values())
            panels.append(render(blind_cap, 5670, t, point,
                                 f"chair {t}s  cap={pixels}"))
    finally:
        positive_cap.release()
        blind_cap.release()
    image_path = OUT / "end6-highres-body-handle-source-review.jpg"
    if not cv2.imwrite(str(image_path),
                       np.vstack([np.hstack(panels[:4]), np.hstack(panels[4:])]),
                       [cv2.IMWRITE_JPEG_QUALITY, 90]):
        raise RuntimeError("Could not write source sheet")
    result = {
        "status": "selected_source_illustration_not_independent_event_validation",
        "body_probe_sha256": digest(BODY),
        "handle_screen_sha256": digest(SCREEN),
        "positive_video_sha256": digest(POSITIVE),
        "blind_video_sha256": digest(BLIND),
        "runner_sha256": digest(Path(__file__)),
        "image_sha256": digest(image_path),
        "positive_times_s": POSITIVE_TIMES,
        "false_path_id": "B006",
        "false_path_times_s": [6229, 6230, 6231, 6232],
        "same_agent_source_review": {
            "positive": "visible_moving_yellow_stone",
            "false_path": "moving_wheelchair_back_not_stone",
        },
        "independent_event_labels": False,
    }
    (OUT / "end6-highres-body-handle-source-review.json").write_text(
        json.dumps(result, indent=2) + "\n")
    print(image_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
