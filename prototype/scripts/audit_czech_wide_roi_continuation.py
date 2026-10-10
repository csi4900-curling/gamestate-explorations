"""Probe unique same-colour continuation from two Czech raw proposal tracks."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from throw_detection import PassageConfig, stone_candidates  # noqa: E402
from wide_roi_continuation import next_observation  # noqa: E402

BASE = ROOT / "validation/throw-event-benchmark"
VIDEO = BASE / "canada-czech-2024/source-360p.mp4"
PATHS = {
    "S96": BASE / "layout-router/camera-motion-integrated-czech24-s96-negative/raw-with-continuation-development.json",
    "S143": BASE / "layout-router/czech24-full-camera-motion-v1/s143-raw-with-continuation-development.json",
}
TIMES = {"S96": 4037.326, "S143": 6374.697}
OUT = BASE / "layout-router/czech24-full-camera-motion-v1/wide-roi-continuation-pilot.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Pilot exists")
    source_hash = digest(VIDEO)
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise ValueError("Source unreadable")
    fps = cap.get(cv2.CAP_PROP_FPS)
    config = PassageConfig(roi=(0, 4, 320, 300))
    rows = []
    try:
        for full_id, path in PATHS.items():
            raw = json.loads(path.read_text())
            if raw["source_sha256"] != source_hash:
                raise ValueError("Replay source differs")
            event = min(raw["events"], key=lambda e: abs(
                e["crossing_time_s"] - TIMES[full_id]))
            if abs(event["crossing_time_s"] - TIMES[full_id]) > 0.001:
                raise ValueError("Source proposal did not replay")
            seed = event["continued_track_points"]
            path_points = [dict(p) for p in seed]
            start = seed[-1]["time_s"]
            status = "probe_interval_end"
            attempted = []
            for step in range(1, 31):
                t = round(start + step * 0.1, 3)
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
                ok, frame = cap.read()
                if not ok:
                    status = "source_decode_failed"
                    break
                detections = [p for p in stone_candidates(frame, config)
                              if p["colour"] == event["colour"]]
                chosen, decision = next_observation(path_points, detections, t)
                attempted.append({"time_s": t, "same_colour_candidates":
                                  len(detections), "decision": decision})
                if chosen is None:
                    status = decision
                    break
                path_points.append(chosen)
            rows.append({"full_match_candidate_id": full_id,
                         "short_replay_candidate_id": event["id"],
                         "crossing_time_s": event["crossing_time_s"],
                         "seed_point_count": len(seed),
                         "new_point_count": len(path_points) - len(seed),
                         "stop_reason": status,
                         "observed_image_path": path_points,
                         "attempted_frames": attempted})
    finally:
        cap.release()
    OUT.write_text(json.dumps({
        "status": "conservative_wide_roi_continuation_development_not_identity_truth",
        "source_sha256": source_hash,
        "input_sha256": {id: digest(path) for id, path in PATHS.items()},
        "code_sha256": {"candidate_detector": digest(ROOT /
            "prototype/throw_detection.py"),
            "continuation": digest(ROOT /
                "prototype/wide_roi_continuation.py"),
            "runner": digest(Path(__file__))},
        "search_roi_640x360": list(config.roi),
        "rows": rows,
        "limitations": [
            "These are selected known development cases and only same-colour image associations.",
            "The first missing or competing candidate stops the path; no hidden interval or camera cut is bridged.",
            "A unique image contour is not proven to be the original physical stone or person.",
        ],
    }, indent=2) + "\n")
    print(json.dumps([{k: r[k] for k in (
        "full_match_candidate_id", "new_point_count", "stop_reason")}
        for r in rows]))


if __name__ == "__main__":
    main()
