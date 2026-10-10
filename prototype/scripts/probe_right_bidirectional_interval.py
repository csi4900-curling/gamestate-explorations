"""Run the fixed 2024 bidirectional right-view proposal on a source interval."""

import argparse
import json
from pathlib import Path

import cv2

from probe_right_bidirectional_clip import (bidirectional_spans, digest,
                                            moving_cap_tracks,
                                            right_colour_proposals, ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--source-start", type=int, required=True)
    parser.add_argument("--source-stop", type=int, required=True)
    parser.add_argument("--source-offset", type=int, default=0,
                        help="Source time represented by local video time zero")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    if not (0 <= args.source_offset <= args.source_start < args.source_stop):
        parser.error("Invalid source interval or video offset")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
    if args.source_stop - args.source_offset > duration:
        parser.error("Declared source interval exceeds reported video duration")
    observations = {"red": [], "yellow": []}
    try:
        for source_second in range(args.source_start, args.source_stop + 1):
            local_second = source_second - args.source_offset
            cap.set(cv2.CAP_PROP_POS_FRAMES, round(local_second * fps))
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Could not decode source second {source_second}")
            frame = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
            colours = right_colour_proposals(frame)
            for colour in observations:
                observations[colour].append((float(source_second), colours[colour]))
    finally:
        cap.release()
    tracks = []
    for colour, samples in observations.items():
        for path in moving_cap_tracks(samples, max_gap_s=1, max_step_px=40):
            tracks.append({"colour": colour, "points": path["points"],
                           "span_px": path["span_px"]})
    tracks.sort(key=lambda row: (row["points"][0]["time_s"], row["colour"]))
    for index, row in enumerate(tracks, 1):
        row["track_id"] = f"B{index:03d}"
    proposals = bidirectional_spans(tracks)
    result = {
        "status": "2024_interval_bidirectional_right_proposals_not_physical_throw_labels",
        "source_sha256": digest(args.video),
        "video_size_bytes": args.video.stat().st_size,
        "source_interval_s": [args.source_start, args.source_stop],
        "source_time_offset_s": args.source_offset,
        "sample_period_s": 1,
        "maximum_inter_sample_gap_s": 1,
        "maximum_step_px_per_s": 40,
        "colour_proposal_code_sha256": digest(
            ROOT / "prototype/scripts/probe_static_left_right_cap_motion.py"),
        "tracker_code_sha256": digest(ROOT / "prototype/stone_motion_fallback.py"),
        "bidirectional_code_sha256": digest(ROOT / "prototype/right_bidirectional_span.py"),
        "runner_sha256": digest(Path(__file__)),
        "raw_track_count": len(tracks),
        "directional_proposal_count": len(proposals),
        "raw_tracks": tracks,
        "directional_review_proposals": proposals,
        "limitations": [
            "Right-colour proposal parameters were fitted to the 2024 production family.",
            "A coloured path can follow a person or switch identity; no throw is accepted.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"raw_tracks": len(tracks), "review_proposals": len(proposals),
                      "duration_s": duration}))


if __name__ == "__main__":
    main()
