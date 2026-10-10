"""Source-review every upward red body/handle path in candidate windows."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark"
VIDEO = BASE / "canada-latvia-2024/source-1080p-1650-2760.mp4"
OUT = BASE / "layout-router/full-2024-coverage/latvia24-full-v1"
SOURCE_REVIEW = {
    "S49": {"moving_prefix": "source_visible_moving_red_stone",
            "tail": "identity_switch_or_parked_stone_possible"},
    "S53": {"moving_prefix": "source_visible_moving_red_stone",
            "tail": "source_visible_moving_red_stone"},
    "S56": {"moving_prefix": "source_visible_moving_red_stone",
            "tail": "source_visible_moving_red_stone"},
    "S59": {"moving_prefix": "source_visible_moving_red_stone",
            "tail": "settled_identity_unverified"},
    "S63": {"moving_prefix": "source_visible_moving_red_stone",
            "tail": "source_visible_moving_red_stone"},
    "S65": {"moving_prefix": "source_visible_moving_red_stone",
            "tail": "settled_identity_unverified"},
}


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ledgers = sorted(OUT.glob("early-highres-red-window-S*.json"))
    if len(ledgers) != 9:
        raise ValueError("Expected all nine red candidate windows")
    rows = []
    for path in ledgers:
        item = json.loads(path.read_text())
        if item["source_video_sha256"] != digest(VIDEO):
            raise ValueError(f"Source mismatch: {path}")
        for track in item["supported_image_paths"]:
            if track["direction"] == "upward":
                rows.append((path, item, track))
    if not rows:
        raise ValueError("No upward paths")
    if {item["candidate_id"].split("-")[-1] for _, item, _ in rows} != set(SOURCE_REVIEW):
        raise ValueError("Upward set changed; source review must be repeated")
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    panels, manifest = [], []
    try:
        for path, item, track in rows:
            points = track["points"]
            selected = [points[0], points[len(points)//2], points[-1]]
            row = []
            for point in selected:
                t = point["time_s"]
                capture.set(cv2.CAP_PROP_POS_MSEC, (t-1650)*1000)
                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError(f"Cannot decode {t} s")
                view = cv2.resize(frame[:, 960:], (480, 540),
                                  interpolation=cv2.INTER_AREA)
                x, y = point["center_1080p_px"]
                x = round((x-960)/2)
                y = round(y/2)
                cv2.rectangle(view, (x-24, y-18), (x+24, y+18),
                              (255, 0, 255), 2)
                cv2.rectangle(view, (0, 0), (480, 38), (10, 20, 30), -1)
                cv2.putText(view, f"{item['candidate_id'].split('-')[-1]} {t}s",
                            (8, 27), cv2.FONT_HERSHEY_SIMPLEX,
                            .75, (255, 255, 255), 2)
                row.append(view)
            panels.append(np.hstack(row))
            manifest.append({"candidate_id": item["candidate_id"],
                             "ledger_sha256": digest(path),
                             "selected_times_s": [p["time_s"] for p in selected],
                             "path_interval_s": [track["first_observed_s"],
                                                 track["last_observed_s"]]})
    finally:
        capture.release()
    image_path = OUT / "early-highres-red-upward-source-review.jpg"
    if not cv2.imwrite(str(image_path), np.vstack(panels),
                       [cv2.IMWRITE_JPEG_QUALITY, 90]):
        raise RuntimeError("Cannot save source sheet")
    result = {
        "status": "prediction_selected_red_upward_paths_source_sheet_not_event_validation",
        "video_sha256": digest(VIDEO),
        "runner_sha256": digest(Path(__file__)),
        "image_sha256": digest(image_path),
        "paths": manifest,
        "same_agent_source_review": SOURCE_REVIEW,
        "independent_event_labels": False,
    }
    (OUT / "early-highres-red-upward-source-review.json").write_text(
        json.dumps(result, indent=2) + "\n")
    print(image_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
