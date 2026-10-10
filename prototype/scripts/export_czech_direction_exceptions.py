"""Export unmarked source frames for the two Czech direction exceptions."""

from hashlib import sha256
import json
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark"
VIDEO = BASE / "canada-czech-2024/source-360p.mp4"
RAW = BASE / "layout-router/czech24-full-camera-motion-v1/run-02/raw.json"
DIRECTION = BASE / "layout-router/czech24-full-camera-motion-v1/end-conditioned-motion-direction-development.json"
OUT = BASE / "layout-router/czech24-full-camera-motion-v1/direction-exception-source"
TIMES = {"S18": (594.0, 596.0, 596.3),
         "S103": (4361.6, 4361.9, 4362.3)}


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Exception source packet exists")
    raw, direction = (json.loads(p.read_text()) for p in (RAW, DIRECTION))
    exceptions = {id for run in direction["rows"] for id in
                  run["opposite_direction_candidate_ids"]}
    if (digest(VIDEO) != raw["source_sha256"] or
            direction["input_sha256"]["raw"] != digest(RAW) or
            exceptions != set(TIMES)):
        raise ValueError("Source or exception inventory differs")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise ValueError("Source unreadable")
    fps = cap.get(cv2.CAP_PROP_FPS)
    OUT.mkdir(parents=True)
    rows = []
    try:
        for id, times in TIMES.items():
            event = next(e for e in raw["events"] if e["id"] == id)
            points = {p["time_s"]: p for p in event["observed_track_points"]}
            if any(t not in points for t in times):
                raise ValueError(f"Selected source point absent: {id}")
            frames = []
            for t in times:
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
                ok, frame = cap.read()
                if not ok:
                    raise ValueError(f"Frame unreadable at {t}")
                name = f"{id}-{t:.1f}.png"
                path = OUT / name
                if not cv2.imwrite(str(path), frame):
                    raise ValueError(f"Frame write failed: {path}")
                frames.append({"source_time_s": t,
                               "video_frame_index": int(cap.get(
                                   cv2.CAP_PROP_POS_FRAMES)) - 1,
                               "file": name, "sha256": digest(path),
                               "raw_track_pixel": points[t]["pixel"],
                               "raw_track_bbox": points[t]["bbox"]})
            rows.append({"candidate_id": id,
                         "crossing_time_s": event["crossing_time_s"],
                         "colour_claim": event["colour"],
                         "view_motion": event["view_motion"],
                         "frames": frames})
    finally:
        cap.release()
    (OUT / "manifest.json").write_text(json.dumps({
        "status": "unmarked_source_frames_for_agent_review_not_independent_labels",
        "source_video_sha256": raw["source_sha256"],
        "input_sha256": {"raw": digest(RAW), "direction": digest(DIRECTION)},
        "runner_sha256": digest(Path(__file__)),
        "rows": rows,
    }, indent=2) + "\n")
    print(json.dumps({"candidates": len(rows),
                      "source_frames": sum(len(row["frames"]) for row in rows)}))


if __name__ == "__main__":
    main()
