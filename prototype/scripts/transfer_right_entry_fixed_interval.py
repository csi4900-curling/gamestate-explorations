"""Replay frozen right-view entry proposal rules on a declared 2024 interval.

This exports raw motion and the post-Latvia entry tier, not verified throws.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from stone_motion_fallback import moving_cap_tracks
from right_view_entry_triage import triage_tracks
from probe_static_left_right_cap_motion import right_colour_proposals


def digest(path):
    value = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--stop", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.start < 0 or args.stop <= args.start:
        parser.error("Invalid interval or output already exists")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    if args.stop > cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps:
        parser.error("Interval exceeds video duration")
    observations = {"red": [], "yellow": []}
    try:
        for time_s in range(args.start, args.stop + 1):
            cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Could not decode {time_s} s")
            proposals = right_colour_proposals(frame)
            for colour in observations:
                observations[colour].append((float(time_s), proposals[colour]))
    finally:
        cap.release()
    tracks = []
    for colour, samples in observations.items():
        for path in moving_cap_tracks(samples, max_gap_s=2, max_step_px=25):
            tracks.append(
                {
                    "colour": colour,
                    "first_observed_s": path["points"][0]["time_s"],
                    "last_observed_s": path["points"][-1]["time_s"],
                    "observation_count": len(path["points"]),
                    "span_px": path["span_px"],
                    "points": path["points"],
                    "physical_throw_verified": False,
                }
            )
    tracks.sort(key=lambda row: (row["first_observed_s"], row["colour"]))
    for index, row in enumerate(tracks, 1):
        row["track_id"] = f"R{index:03d}"
    entries = triage_tracks(tracks)
    selected = {row["raw_track_id"] for row in entries}
    result = {
        "status": "frozen_postlatvia_right_entry_transfer_not_event_validation",
        "source_id": args.source_id,
        "source_sha256": digest(args.video),
        "source_interval_s": [args.start, args.stop],
        "sample_period_s": 1,
        "raw_proposal_count_by_colour": {
            colour: sum(len(candidates) for _, candidates in samples)
            for colour, samples in observations.items()
        },
        "raw_track_count": len(tracks),
        "entry_review_count": len(entries),
        "raw_tracks": tracks,
        "entry_review_proposals": entries,
        "unpromoted_raw_track_ids": [
            row["track_id"] for row in tracks if row["track_id"] not in selected
        ],
        "proposal_code_sha256": digest(
            ROOT / "prototype/scripts/probe_static_left_right_cap_motion.py"
        ),
        "tracker_code_sha256": digest(ROOT / "prototype/stone_motion_fallback.py"),
        "triage_code_sha256": digest(ROOT / "prototype/right_view_entry_triage.py"),
        "runner_sha256": digest(Path(__file__)),
        "limitations": [
            "The right-entry tier was fitted after Latvia source inspection.",
            "The fixed interval is shared with prior exposed 2024 development work.",
            "A proposal is not a verified delivered stone; independent event F1 is not estimated.",
            "Tracks can switch identity, and a camera change can create false image motion.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"raw_tracks": len(tracks), "entry_review": len(entries)}))


if __name__ == "__main__":
    main()
