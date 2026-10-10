"""Explore stone-cap motion in the lower delivery ice on predicted shot views.

This is a post-transfer diagnostic. It must not overwrite the frozen cap audit
or be reported as an independent event score.
"""

import argparse
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from origin_release_ice_support import below_ice_fraction
from stone_motion_fallback import moving_cap_tracks, stone_cap_candidates


def ice_cap_candidates(frame, colour):
    """Keep candidates over broad lower ice, away from people at rink edge."""
    kept = []
    for candidate in stone_cap_candidates(frame, colour, allow_bright_body=True,
                                           allow_large_caps=True):
        x, y = candidate["pixel"]
        if not (200 <= x <= 550 and y >= 240):
            continue
        ice = below_ice_fraction(frame, candidate["pixel"])
        if ice is not None and ice >= 0.6:
            kept.append({**candidate, "below_ice_fraction": ice})
    return kept


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--origins", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first diagnostic result")
    source_hash = file_sha256(args.video)
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash == reserved["source_sha256"]:
        parser.error("Reserved independent source cannot be used for development")
    origins = json.loads(args.origins.read_text())
    if origins["source_sha256"] != source_hash:
        parser.error("Origin predictions use a different source video")
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        parser.error("Video cannot be opened")
    fps = capture.get(cv2.CAP_PROP_FPS)
    step = round(fps / 5)
    if fps <= 0 or step <= 0:
        parser.error("Invalid video frame rate")
    rows = []
    total_samples = 0
    for origin in origins["rows"]:
        if not origin["predicted"]:
            continue
        start, end = origin["interval_s"]
        first, last = round(start * fps), round(end * fps)
        capture.set(cv2.CAP_PROP_POS_FRAMES, first)
        observations = {"red": [], "yellow": []}
        samples = 0
        for frame_index in range(first, last):
            if not capture.grab():
                raise RuntimeError(f"Decode failed at frame {frame_index}")
            if frame_index % step:
                continue
            ok, frame = capture.retrieve()
            if not ok:
                raise RuntimeError(f"Retrieve failed at frame {frame_index}")
            time_s = round(frame_index / fps, 3)
            for colour in observations:
                observations[colour].append(
                    (time_s, ice_cap_candidates(frame, colour)))
            samples += 1
        tracks = {}
        for colour, events in observations.items():
            tracks[colour] = [
                {"interval_s": [row["points"][0]["time_s"],
                                 row["points"][-1]["time_s"]],
                 "span_px": round(row["span_px"], 2),
                 "point_count": len(row["points"]),
                 "first_pixel": row["points"][0]["pixel"],
                 "last_pixel": row["points"][-1]["pixel"]}
                for row in moving_cap_tracks(events, max_gap_s=1.6,
                                             max_step_px=130)
            ]
        rows.append({"shot_id": origin["shot_id"],
                     "interval_s": origin["interval_s"],
                     "sample_count": samples,
                     "observation_count": {colour: sum(len(items) for _, items in events)
                                           for colour, events in observations.items()},
                     "tracks": tracks,
                     "supported_colours": [colour for colour in tracks if tracks[colour]]})
        total_samples += samples
    capture.release()
    result = {
        "status": "post_transfer_development_delivery_ice_cap_diagnostic_not_event_f1",
        "source_sha256": source_hash,
        "source_interval_s": origins["source_interval_s"],
        "origins_sha256": file_sha256(args.origins),
        "cap_code_sha256": file_sha256(ROOT / "prototype/stone_motion_fallback.py"),
        "ice_code_sha256": file_sha256(ROOT / "prototype/origin_release_ice_support.py"),
        "runner_sha256": file_sha256(__file__),
        "gate": {"x_px": [200, 550], "min_y_px": 240,
                 "min_below_ice_fraction": 0.6, "frame_size_px": [640, 360]},
        "selection_rule": "All predicted shot-origin windows; no counter or official labels select windows.",
        "scanned_window_count": len(rows),
        "sample_count": total_samples,
        "rows": rows,
        "limitations": [
            "Post-transfer diagnostic; the geometry was developed on Beijing 2022 footage.",
            "This rejects stones outside the lower delivery view and cannot stand alone as a complete-recording detector.",
            "A moving person or other object over ice can still supply a false coloured track.",
            "Tracks are not object-identity links across hard camera cuts.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print({"windows": len(rows), "samples": total_samples,
           "supported": sum(bool(row["supported_colours"]) for row in rows)})


if __name__ == "__main__":
    main()
