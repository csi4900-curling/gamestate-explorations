"""Replay a frozen raw 2024 span pass and retain each emitted image track."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from span_passage_detection import SpanPassageDetector
from throw_detection import stone_candidates


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--raw", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve the first replay")
    frozen = json.loads(args.raw.read_text())
    if digest(args.video) != frozen["source_sha256"]:
        parser.error("Source differs from frozen raw pass")
    if frozen["model_sha256"] != digest(ROOT / "prototype/span_passage_detection.py"):
        parser.error("Span detector code differs from frozen pass")
    if frozen["baseline_sha256"] != digest(ROOT / "prototype/throw_detection.py"):
        parser.error("Proposal/tracker code differs from frozen pass")
    if frozen["runner_sha256"] != digest(ROOT / "prototype/scripts/run_span_probe.py"):
        parser.error("Original raw runner code differs")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if frozen["source_sha256"] == reserved["source_sha256"]:
        parser.error("Reserved source cannot be used for development")
    start, end = frozen["source_interval_s"]
    cv2.setNumThreads(1)
    detector = SpanPassageDetector()
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps if fps > 0 else 0
    if not 0 <= start < end <= duration:
        raise ValueError("Unreadable source or invalid frozen interval")
    first = round(start * fps)
    step = max(1, round(fps / 10))
    cap.set(cv2.CAP_PROP_POS_FRAMES, first)
    observed_ids = {}
    saved_points = {}
    sample_count = 0
    for frame_number in range(first, round(end * fps)):
        if not cap.grab():
            raise RuntimeError(f"Decode failed at {frame_number / fps:.3f}")
        if (frame_number - first) % step:
            continue
        ok, frame = cap.retrieve()
        if not ok:
            raise RuntimeError(f"Frame retrieval failed at {frame_number / fps:.3f}")
        emitted = detector.update(stone_candidates(frame, detector.config), frame_number / fps)
        for event in emitted:
            if event["track_id"] in observed_ids:
                raise ValueError("One track emitted more than one event")
            observed_ids[event["track_id"]] = event["id"]
        for track in detector.tracker.tracks:
            if track.id in observed_ids:
                # The same track can continue after its first qualifying span.
                saved_points[track.id] = [dict(point) for point in track.points]
        sample_count += 1
    cap.release()
    if sample_count != frozen["samples"] or detector.events != frozen["events"]:
        raise ValueError("Track replay did not exactly reproduce frozen raw events")
    if len(saved_points) != len(detector.events):
        raise ValueError("Not every emitted event retained a track")
    rows = []
    for event in frozen["events"]:
        points = saved_points[event["track_id"]]
        times = [point["time_s"] for point in points]
        crossing = event["crossing_time_s"]
        before = max((t for t in times if t <= crossing), default=None)
        after = min((t for t in times if t >= crossing), default=None)
        if before is None or after is None:
            raise ValueError(f"Crossing unbracketed by captured track: {event['id']}")
        rows.append(
            {
                "event_id": event["id"],
                "track_id": event["track_id"],
                "colour": event["colour"],
                "crossing_time_s": crossing,
                "crossing_time_bracket_s": [before, after],
                "first_track_observation_s": times[0],
                "last_track_observation_s": times[-1],
                "point_count": len(points),
                "points": points,
            }
        )
    output = {
        "status": "exact_raw_span_replay_with_candidate_local_image_tracks_not_physical_identity",
        "source_id": frozen["source_id"],
        "source_sha256": frozen["source_sha256"],
        "source_interval_s": frozen["source_interval_s"],
        "raw_artifact_sha256": digest(args.raw),
        "runner_sha256": digest(Path(__file__)),
        "span_detector_sha256": frozen["model_sha256"],
        "proposal_tracker_sha256": frozen["baseline_sha256"],
        "sample_count": sample_count,
        "reproduced_event_count": len(rows),
        "tracks": rows,
        "limitations": [
            "An image tracker can switch objects, including a stone and a nearby player.",
            "A reproduced motion path is not a verified physical delivered stone.",
            "Points use the 640x360 broadcast image, not rink coordinates.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"reproduced_events": len(rows), "samples": sample_count}))


if __name__ == "__main__":
    main()
