"""Freeze source pixels for two Czech raw stone paths rejected by context."""

from hashlib import sha256
import json
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark"
VIDEO = BASE / "canada-czech-2024/source-360p.mp4"
RUN = BASE / "layout-router/czech24-full-camera-motion-v1/run-02"
RAW = RUN / "raw.json"
EVENTS = RUN / "events.json"
OUT_BASE = BASE / "layout-router/czech24-full-camera-motion-v1"
TIMES = {
    "S04": (191.5, 192.0, 192.5, 194.0, 196.0, 198.0, 200.0, 202.0),
    "S13": (488.2, 488.5, 488.8, 489.1, 490.0, 494.0),
}


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    outputs = {id: OUT_BASE / f"{id.lower()}-raw-source-review" for id in TIMES}
    if any(path.exists() for path in outputs.values()):
        raise ValueError("A withheld-stone source packet already exists")
    raw, events = (json.loads(path.read_text()) for path in (RAW, EVENTS))
    if not (digest(VIDEO) == raw["source_sha256"] == events["source_sha256"]):
        raise ValueError("Input source differs")
    event_by_id = {row["id"]: row for row in raw["events"]}
    decision_by_id = {row["id"]: row for row in events["decisions"]}
    if any(row["id"] in TIMES for row in events["events"]):
        raise ValueError("A reviewed case became context-confirmed")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise ValueError("Source video unreadable")
    fps = cap.get(cv2.CAP_PROP_FPS)
    try:
        for id, times in TIMES.items():
            event, decision = event_by_id[id], decision_by_id[id]
            if (decision["status"] != "unconfirmed" or
                    decision["reason"] != "large_surrounding_motion"):
                raise ValueError(f"{id} context decision changed")
            points = {point["time_s"]: point for point in
                      event["observed_track_points"]}
            if any(t not in points for t in times[:3]):
                raise ValueError(f"{id} expected raw points missing")
            out = outputs[id]
            out.mkdir(parents=True)
            frames = []
            for time_s in times:
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise ValueError(f"Cannot decode source frame at {time_s}")
                path = out / f"source-{time_s:.1f}.png"
                if not cv2.imwrite(str(path), frame):
                    raise ValueError(f"Cannot write {path}")
                point = points.get(time_s)
                frames.append({"source_time_s": time_s,
                               "video_frame_index": int(cap.get(
                                   cv2.CAP_PROP_POS_FRAMES)) - 1,
                               "file": path.name, "sha256": digest(path),
                               "raw_track_pixel": point["pixel"] if point else None,
                               "raw_track_bbox": point["bbox"] if point else None})
            manifest = {
                "status": "unmarked_source_frames_for_agent_review_not_independent_labels",
                "source_video_sha256": raw["source_sha256"],
                "input_sha256": {"raw": digest(RAW), "events": digest(EVENTS)},
                "runner_sha256": digest(Path(__file__)),
                "candidate_id": id,
                "crossing_time_s": event["crossing_time_s"],
                "raw_view_motion": event["view_motion"],
                "context_decision": decision,
                "frames": frames,
            }
            (out / "manifest.json").write_text(json.dumps(
                manifest, indent=2) + "\n")
    finally:
        cap.release()
    print(json.dumps({"candidates": list(TIMES),
                      "source_frames": sum(map(len, TIMES.values()))}))


if __name__ == "__main__":
    main()
