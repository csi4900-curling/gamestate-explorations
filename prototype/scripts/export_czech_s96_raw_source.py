"""Export exact source frames for review of the raw S96 trigger pixels."""

from hashlib import sha256
import json
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark"
VIDEO = BASE / "canada-czech-2024/source-360p.mp4"
RAW = BASE / "layout-router/czech24-full-camera-motion-v1/run-02/raw.json"
OUT = BASE / "layout-router/czech24-full-camera-motion-v1/s96-raw-source-review"
TIMES = (4036.8, 4037.6, 4038.2)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Source packet exists")
    raw = json.loads(RAW.read_text())
    if digest(VIDEO) != raw["source_sha256"]:
        raise ValueError("Source video differs")
    event = next(e for e in raw["events"] if e["id"] == "S96")
    points = {p["time_s"]: p for p in event["observed_track_points"]}
    points.update({p["time_s"]: p for p in event.get("continued_track_points", [])})
    replay_digest = None
    if not all(t in points for t in TIMES):
        # The full run predates continued-track output; the last frame's
        # point comes from a matching short source replay of this candidate.
        replay_path = (
            BASE
            / "layout-router/camera-motion-integrated-czech24-s96-negative/raw-with-continuation-development.json"
        )
        replay = json.loads(replay_path.read_text())
        replay_digest = digest(replay_path)
        if replay["source_sha256"] != raw["source_sha256"]:
            raise ValueError("Short replay source differs")
        matched = next(
            e for e in replay["events"] if e["crossing_time_s"] == event["crossing_time_s"]
        )
        points.update({p["time_s"]: p for p in matched["continued_track_points"]})
    if not all(t in points for t in TIMES):
        raise ValueError("Selected point absent from source track")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise ValueError("Source unreadable")
    fps = cap.get(cv2.CAP_PROP_FPS)
    OUT.mkdir(parents=True)
    frames = []
    try:
        for t in TIMES:
            cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
            ok, frame = cap.read()
            if not ok:
                raise ValueError(f"Frame unreadable at {t}")
            name = f"source-{t:.1f}.png"
            path = OUT / name
            if not cv2.imwrite(str(path), frame):
                raise ValueError(f"Frame write failed: {path}")
            frames.append(
                {
                    "source_time_s": t,
                    "decoded_frame_index": int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1,
                    "file": name,
                    "sha256": digest(path),
                    "raw_track_pixel": points[t]["pixel"],
                    "raw_track_bbox": points[t]["bbox"],
                }
            )
    finally:
        cap.release()
    (OUT / "manifest.json").write_text(
        json.dumps(
            {
                "status": "unmarked_source_frames_for_agent_review_not_independent_label",
                "source_video_sha256": raw["source_sha256"],
                "raw_sha256": digest(RAW),
                "continuation_replay_sha256": replay_digest,
                "runner_sha256": digest(Path(__file__)),
                "candidate_id": "S96",
                "crossing_time_s": event["crossing_time_s"],
                "frames": frames,
                "limitations": [
                    "The points are image-track detections; physical object identity is not automated here.",
                    "A human review of this packet is same-agent development evidence, not an independent exhaustive throw label.",
                ],
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps({"frames": len(frames), "candidate_time_s": event["crossing_time_s"]}))


if __name__ == "__main__":
    main()
