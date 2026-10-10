"""Selected source audit of a second, red-stone 1080p body template.

This is postfailure development evidence; it is not a held-out detector test.
"""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from probe_latvia_1080p_body_paths import frame_at, matches
from screen_latvia_body_with_handle import handle_evidence

BASE = ROOT / "validation/throw-event-benchmark"
VIDEO = BASE / "canada-latvia-2024/source-1080p-1650-2760.mp4"
TRANSFER = BASE / "layout-router/full-2024-coverage/latvia24-full-v1/early-highres-body-handle-transfer-development.json"
OUT = BASE / "layout-router/full-2024-coverage/latvia24-full-v1"
TEMPLATE_SOURCE_TIME_S = 1991
TEMPLATE_XYXY = (1540, 777, 1620, 814)
TIMES = (1989, 1990, 1991, 1992, 1993, 2364, 2365, 2366, 2367, 2368,
         2309, 2311)
SHEET_TIMES = (1989, 1991, 1993, 2364, 2366, 2368)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    json_path = OUT / "early-highres-red-template-selected-development.json"
    image_path = OUT / "early-highres-red-moving-source-review.jpg"
    if json_path.exists() or image_path.exists():
        raise SystemExit("Output exists; preserve first diagnostic")
    transfer = json.loads(TRANSFER.read_text())
    video_hash = digest(VIDEO)
    if transfer["source_video_sha256"] != video_hash:
        raise ValueError("Video differs from transfer")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Cannot open source video")
    rows, panels = [], {}
    try:
        source = frame_at(cap, TEMPLATE_SOURCE_TIME_S-1650)
        x1, y1, x2, y2 = TEMPLATE_XYXY
        template = cv2.resize(
            cv2.cvtColor(source[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY),
            (40, 19), interpolation=cv2.INTER_AREA)
        for t in TIMES:
            frame = frame_at(cap, t-1650)
            proposed = [{**p, **handle_evidence(frame, p)}
                        for p in matches(frame, template)]
            rows.append({"time_s": t, "body_proposals": proposed})
            if t in SHEET_TIMES:
                view = cv2.resize(frame[:, 960:], (480, 540),
                                  interpolation=cv2.INTER_AREA)
                cv2.rectangle(view, (0, 0), (480, 38), (10, 20, 30), -1)
                cv2.putText(view, str(t), (8, 28), cv2.FONT_HERSHEY_SIMPLEX,
                            .8, (255, 255, 255), 2)
                panels[t] = view
    finally:
        cap.release()
    sheet = np.vstack([
        np.hstack([panels[t] for t in SHEET_TIMES[:3]]),
        np.hstack([panels[t] for t in SHEET_TIMES[3:]]),
    ])
    if not cv2.imwrite(str(image_path), sheet,
                       [cv2.IMWRITE_JPEG_QUALITY, 90]):
        raise RuntimeError("Could not save red source sheet")
    result = {
        "status": "postfailure_selected_red_template_development_not_event_validation",
        "video_sha256": video_hash,
        "earlier_transfer_sha256": digest(TRANSFER),
        "runner_sha256": digest(Path(__file__)),
        "body_code_sha256": digest(
            ROOT / "prototype/scripts/probe_latvia_1080p_body_paths.py"),
        "handle_code_sha256": digest(
            ROOT / "prototype/scripts/screen_latvia_body_with_handle.py"),
        "source_sheet_sha256": digest(image_path),
        "template_source_time_s": TEMPLATE_SOURCE_TIME_S,
        "template_xyxy_1080p": TEMPLATE_XYXY,
        "source_review_times_s": SHEET_TIMES,
        "sample_times_s": TIMES,
        "samples": rows,
        "same_agent_source_review": {
            "1989_1993": "red_stone_visibly_moves_toward_house",
            "2364_2368": "red_stone_visibly_moves_toward_house_then_near_other_stones",
        },
        "limitations": [
            "Template and timestamps were selected after yellow-template transfer failed on red events.",
            "The red template also matches parked stones and some yellow stones.",
            "These selected examples do not measure full-interval or cross-video recall.",
        ],
    }
    json_path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
