"""Measure white-ice scene coverage for every provisional throw candidate."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ice_fractions(frame):
    image = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    ice = (hsv[:, :, 1] < 75) & (hsv[:, :, 2] > 165)
    return {"whole": round(float(np.mean(ice)), 4),
            "lower_half": round(float(np.mean(ice[180:])), 4),
            "center_lower": round(float(np.mean(ice[180:, 160:480])), 4)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first scene audit")
    source_hash = digest(args.video)
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash == reserved["source_sha256"]:
        parser.error("Reserved independent source cannot be used for development")
    ledger = json.loads(args.candidates.read_text())
    if ledger["source_sha256"] != source_hash:
        parser.error("Source video and candidate ledger differ")
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        parser.error("Cannot open source video")
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    for event in ledger["events"]:
        start, end = event["release_window_s"]
        samples = []
        for fraction in (0.25, 0.5, 0.75):
            time_s = start + fraction * (end - start)
            capture.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Frame decode failed at {time_s}")
            samples.append({"time_s": round(time_s, 3),
                            "ice_fraction": ice_fractions(frame)})
        rows.append({"candidate_id": event["candidate_id"],
                     "shot_id": event["shot_id"],
                     "counter_backed": event["counter_id"] is not None,
                     "samples": samples,
                     "median_ice_fraction": {key: round(float(np.median([
                         row["ice_fraction"][key] for row in samples])), 4)
                         for key in ("whole", "lower_half", "center_lower")}})
    capture.release()
    output = {
        "status": "source_only_candidate_ice_coverage_diagnostic_not_throw_decision",
        "source_sha256": source_hash,
        "source_interval_s": ledger["source_interval_s"],
        "candidate_ledger_sha256": digest(args.candidates),
        "runner_sha256": digest(Path(__file__)),
        "selection_rule": "All candidate release windows, at 25/50/75 percent of each interval; no official shot labels select windows.",
        "ice_definition": "HSV saturation <75 and value >165 in 640x360 BGR-decoded frame",
        "candidate_count": len(rows),
        "rows": rows,
        "limitations": [
            "Bright clothing and rink graphics can also satisfy the ice colour test.",
            "A genuine throw can be visible only in a short interval missed by three samples.",
            "Ice coverage is camera/view context, not physical stone identity or event evidence.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print({"candidates": len(rows)})


if __name__ == "__main__":
    main()
