"""Scan one 2024 interval for faster bidirectional right-colour paths."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from probe_static_left_right_cap_motion import right_colour_proposals
from right_bidirectional_span import bidirectional_spans
from stone_motion_fallback import moving_cap_tracks


def digest(path):
    result = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def window_ids(proposals, reference, time_key):
    return {
        event["id"]
        for event in reference["events"]
        for proposal in proposals
        if proposal["colour_claim"] == event["colour"]
        and event["delivery_interval_s"][0]
        <= proposal[time_key]["time_s"]
        <= event["delivery_interval_s"][1]
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "variant", "reference", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    variant = json.loads(args.variant.read_text())
    reference = json.loads(args.reference.read_text())
    source_hash = digest(args.video)
    if source_hash != variant["source_sha256"] or source_hash != reference["source_sha256"]:
        parser.error("Source fingerprints differ")
    if variant["source_interval_s"] != reference["source_interval_s"]:
        parser.error("Source intervals differ")
    start, stop = variant["source_interval_s"]
    if start != int(start) or stop != int(stop):
        parser.error("Expected integer-second source interval")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    observations = {"red": [], "yellow": []}
    try:
        for second in range(int(start), int(stop) + 1):
            cap.set(cv2.CAP_PROP_POS_FRAMES, round(second * fps))
            ok, frame = cap.read()
            if not ok or frame.shape[:2] != (360, 640):
                raise RuntimeError(f"Cannot decode 640x360 source second {second}")
            colours = right_colour_proposals(frame)
            for colour in observations:
                observations[colour].append((float(second), colours[colour]))
    finally:
        cap.release()
    tracks = []
    for colour, samples in observations.items():
        for path in moving_cap_tracks(samples, max_gap_s=1, max_step_px=40):
            tracks.append({"colour": colour, "points": path["points"], "span_px": path["span_px"]})
    tracks.sort(key=lambda row: (row["points"][0]["time_s"], row["colour"]))
    for index, row in enumerate(tracks, 1):
        row["track_id"] = f"B{index:03d}"
    proposals = bidirectional_spans(tracks)
    prior = variant["entry_review_proposals"]
    prior_windows = window_ids(prior, reference, "entry_crossing")
    new_windows = window_ids(proposals, reference, "passage")
    all_windows = {row["id"] for row in reference["events"]}
    result = {
        "status": "development_bidirectional_fast_right_track_probe_not_event_validation",
        "source_sha256": source_hash,
        "source_interval_s": variant["source_interval_s"],
        "video_size_bytes": args.video.stat().st_size,
        "variant_sha256": digest(args.variant),
        "coarse_reference_sha256": digest(args.reference),
        "colour_proposal_code_sha256": digest(
            ROOT / "prototype/scripts/probe_static_left_right_cap_motion.py"
        ),
        "tracker_code_sha256": digest(ROOT / "prototype/stone_motion_fallback.py"),
        "bidirectional_code_sha256": digest(ROOT / "prototype/right_bidirectional_span.py"),
        "runner_sha256": digest(Path(__file__)),
        "sample_period_s": 1,
        "maximum_inter_sample_gap_s": 1,
        "maximum_step_px_per_s": 40,
        "raw_track_count": len(tracks),
        "directional_proposal_count": len(proposals),
        "direction_counts": {
            direction: sum(row["direction"] == direction for row in proposals)
            for direction in ("negative_y", "positive_y")
        },
        "coarse_window_count": len(all_windows),
        "coarse_windows_with_existing_variant_prefix": sorted(prior_windows),
        "coarse_windows_with_bidirectional_proposal": sorted(new_windows),
        "newly_covered_coarse_window_ids": sorted(new_windows - prior_windows),
        "still_uncovered_coarse_window_ids": sorted(all_windows - prior_windows - new_windows),
        "raw_tracks": tracks,
        "directional_review_proposals": proposals,
        "limitations": [
            "The 40-pixel step and bidirectional rule were chosen after inspecting an Italy miss.",
            "Greedy colour tracks may switch objects, and player/equipment colours can meet the same motion rule.",
            "Same-colour alignment with five-second-still coarse windows is not independent physical event recall.",
            "This creates review proposals; no throw or game-state acceptance changes.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "tracks": len(tracks),
                "proposals": len(proposals),
                "directions": result["direction_counts"],
                "newly_covered": result["newly_covered_coarse_window_ids"],
                "still_uncovered": result["still_uncovered_coarse_window_ids"],
            }
        )
    )


if __name__ == "__main__":
    main()
