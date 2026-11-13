"""Replay the fixed bidirectional right-view tier on an offset source clip."""

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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--source-offset", type=int, required=True)
    parser.add_argument("--source-stop", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    if args.source_offset < 0 or args.source_stop <= args.source_offset:
        parser.error("Invalid source interval")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open source clip")
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
    last_whole_second = args.source_stop - args.source_offset
    if last_whole_second > duration:
        parser.error("Declared source interval exceeds reported clip duration")
    observations = {"red": [], "yellow": []}
    try:
        for local_second in range(last_whole_second + 1):
            cap.set(cv2.CAP_PROP_POS_FRAMES, round(local_second * fps))
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Could not decode local second {local_second}")
            image = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
            colours = right_colour_proposals(image)
            source_second = float(args.source_offset + local_second)
            for colour in observations:
                observations[colour].append((source_second, colours[colour]))
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
    result = {
        "status": "offset_clip_bidirectional_right_proposals_not_physical_throw_labels",
        "source_sha256": digest(args.video),
        "video_size_bytes": args.video.stat().st_size,
        "source_interval_s": [args.source_offset, args.source_stop],
        "source_time_offset_s": args.source_offset,
        "sample_period_s": 1,
        "maximum_inter_sample_gap_s": 1,
        "maximum_step_px_per_s": 40,
        "colour_proposal_code_sha256": digest(
            ROOT / "prototype/scripts/probe_static_left_right_cap_motion.py"
        ),
        "tracker_code_sha256": digest(ROOT / "prototype/stone_motion_fallback.py"),
        "bidirectional_code_sha256": digest(ROOT / "prototype/right_bidirectional_span.py"),
        "runner_sha256": digest(Path(__file__)),
        "raw_track_count": len(tracks),
        "directional_proposal_count": len(proposals),
        "raw_tracks": tracks,
        "directional_review_proposals": proposals,
        "limitations": [
            "This source clip was processed for development transfer, not as an independent held-out match.",
            "The right colour ROI and motion parameters are fitted to the 2024 split-screen production family.",
            "A proposed colour track can follow a person or switch identity; no physical throw is accepted.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {"raw_tracks": len(tracks), "review_proposals": len(proposals), "duration_s": duration}
        )
    )


if __name__ == "__main__":
    main()
