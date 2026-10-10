"""Post-Italy-score two-second-gap right-view association diagnostic."""

import argparse
import json
from pathlib import Path

import cv2

from probe_right_bidirectional_interval import (digest, right_colour_proposals,
                                                ROOT)
from right_area_aware_tracks import area_aware_tracks
from right_late_seed_span import late_seed_bidirectional_spans


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--source-start", type=int, required=True)
    parser.add_argument("--source-stop", type=int, required=True)
    parser.add_argument("--source-offset", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    if not 0 <= args.source_offset <= args.source_start < args.source_stop:
        parser.error("Invalid source interval or offset")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
    if args.source_stop - args.source_offset > duration:
        parser.error("Declared source interval exceeds video duration")
    observations = {"red": [], "yellow": []}
    try:
        for source_second in range(args.source_start, args.source_stop + 1):
            cap.set(cv2.CAP_PROP_POS_FRAMES, round(
                (source_second - args.source_offset) * fps))
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
        for path in area_aware_tracks(samples, max_gap_s=2):
            tracks.append({"colour": colour, **path})
    tracks.sort(key=lambda row: (row["points"][0]["time_s"], row["colour"]))
    for index, row in enumerate(tracks, 1):
        row["track_id"] = f"A{index:03d}"
    proposals = late_seed_bidirectional_spans(tracks)
    result = {
        "status": "postscore_area_aware_right_proposals_not_physical_throw_labels",
        "source_sha256": digest(args.video),
        "source_interval_s": [args.source_start, args.source_stop],
        "source_time_offset_s": args.source_offset,
        "sample_period_s": 1,
        "maximum_inter_sample_gap_s": 2,
        "maximum_step_px_per_s": 40,
        "area_change_weight_px": 15,
        "minimum_supported_track_points": 3,
        "minimum_supported_track_duration_s": 2,
        "review_span_displacement_px": 60,
        "colour_proposal_code_sha256": digest(
            ROOT / "prototype/scripts/probe_static_left_right_cap_motion.py"),
        "association_code_sha256": digest(ROOT / "prototype/right_area_aware_tracks.py"),
        "late_seed_code_sha256": digest(ROOT / "prototype/right_late_seed_span.py"),
        "runner_sha256": digest(Path(__file__)),
        "raw_track_count": len(tracks),
        "directional_proposal_count": len(proposals),
        "raw_tracks": tracks,
        "directional_review_proposals": proposals,
        "limitations": [
            "The two-second observation gap was chosen after inspecting Italy I04/I16 misses.",
            "Area-continuity weight and late-seed rule were developed after inspecting Canada–USA misses.",
            "Greedy association can still switch identities and lose short tracks.",
            "No path is an accepted physical throw without source and cross-view checks.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"raw_tracks": len(tracks), "review_proposals": len(proposals)}))


if __name__ == "__main__":
    main()
