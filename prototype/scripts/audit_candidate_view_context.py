"""Measure overhead-house context for every provisional event window.

This source-only sidecar preserves candidates and does not make throw decisions.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.video_board_observation_v2 import detect_overhead_house


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first view-context audit")
    source_hash = digest(args.video)
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash == reserved["source_sha256"]:
        parser.error("Reserved independent source cannot be used for development")
    ledger = json.loads(args.candidates.read_text())
    if ledger["source_sha256"] != source_hash:
        parser.error("Candidate ledger uses a different source video")
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        parser.error("Cannot open source video")
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    for event in ledger["events"]:
        start, end = event["release_window_s"]
        if end <= start:
            parser.error("Candidate has an invalid release window")
        samples = []
        for fraction in (0.25, 0.5, 0.75):
            time_s = start + fraction * (end - start)
            capture.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Frame decode failed at {time_s}")
            house = detect_overhead_house(frame)
            samples.append({"time_s": round(time_s, 3),
                            "overhead_house_detected": house is not None,
                            "house_center_px": house["center_px"] if house else None,
                            "house_radius_px": house["outer_radius_px"] if house else None})
        count = sum(row["overhead_house_detected"] for row in samples)
        rows.append({"candidate_id": event["candidate_id"],
                     "shot_id": event["shot_id"],
                     "counter_backed": event["counter_id"] is not None,
                     "release_window_s": event["release_window_s"],
                     "overhead_sample_count": count,
                     "all_samples_overhead": count == len(samples),
                     "samples": samples})
    capture.release()
    output = {
        "status": "source_only_candidate_view_context_diagnostic_not_throw_decision",
        "source_sha256": source_hash,
        "source_interval_s": ledger["source_interval_s"],
        "candidate_ledger_sha256": digest(args.candidates),
        "house_code_sha256": digest(ROOT / "prototype/video_board_observation_v2.py"),
        "runner_sha256": digest(Path(__file__)),
        "selection_rule": "All provisional ledger candidates, three interior frames per candidate; no official shot labels select windows.",
        "candidate_count": len(rows),
        "all_overhead_count": sum(row["all_samples_overhead"] for row in rows),
        "any_overhead_count": sum(row["overhead_sample_count"] > 0 for row in rows),
        "rows": rows,
        "limitations": [
            "An overhead view can show a real delivered stone; view context is not a hard negative label.",
            "The connected-ring detector misses cropped and unusual overhead views.",
            "Three sampled frames may miss a brief camera change within the window.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print({"candidates": len(rows),
           "any_overhead": output["any_overhead_count"],
           "all_overhead": output["all_overhead_count"]})


if __name__ == "__main__":
    main()
