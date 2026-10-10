"""Scan a 2024 broadcast for source-observed active-end chevrons."""

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.scoreboard_end_marker import (fit_header_grid, panel_shift_evidence,
                                             read_active_end_marker)


def digest(path):
    hash_value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hash_value.update(chunk)
    return hash_value.hexdigest()


def scan(video, step_s):
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise ValueError(f"Could not open {video}")
    duration = capture.get(cv2.CAP_PROP_FRAME_COUNT) / capture.get(cv2.CAP_PROP_FPS)
    panel_observations = []
    panel_frames = []
    for time_s in range(120, int(duration), 60):
        capture.set(cv2.CAP_PROP_POS_MSEC, 1000 * time_s)
        okay, frame = capture.read()
        if okay:
            evidence = panel_shift_evidence(frame)
            if evidence is not None:
                panel_observations.append({"time_s": time_s, **evidence})
                panel_frames.append(frame)
    shift = (round(statistics.median(row["shift_px"] for row in panel_observations))
             if len(panel_observations) >= 5 else None)
    geometry = None
    if shift is not None:
        aligned = [frame for frame, row in zip(panel_frames, panel_observations)
                   if abs(row["shift_px"] - shift) <= 3]
        geometry = fit_header_grid(aligned, shift)
    samples = []
    for time_s in range(0, int(duration), step_s):
        capture.set(cv2.CAP_PROP_POS_MSEC, 1000 * time_s)
        okay, frame = capture.read()
        if not okay:
            samples.append({"time_s": time_s, "marker": None, "frame_read_failed": True})
            continue
        samples.append({"time_s": time_s,
                        "marker": read_active_end_marker(
                            frame,
                            x_shift_px=geometry["arrow_origin_x_px"] - 399,
                            slot_pitch_px=geometry["slot_pitch_px"],
                        ) if geometry is not None else None})
    capture.release()
    hits = [row for row in samples if row["marker"] is not None]
    ends = []
    for number in range(1, 9):
        matching = [row for row in hits if row["marker"]["end"] == number]
        if matching:
            ends.append({"end": number, "hit_count": len(matching),
                         "first_hit_s": matching[0]["time_s"],
                         "last_hit_s": matching[-1]["time_s"],
                         "marker_colours": sorted({row["marker"]["colour"] for row in matching})})
    changes = []
    for before, after in zip(hits, hits[1:]):
        old, new = before["marker"]["end"], after["marker"]["end"]
        if old != new:
            changes.append({"from_end": old, "to_end": new,
                            "last_old_hit_s": before["time_s"],
                            "first_new_hit_s": after["time_s"]})
    return duration, shift, geometry, panel_observations, samples, ends, changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--step-s", type=int, default=10)
    args = parser.parse_args()
    if args.step_s <= 0:
        parser.error("step must be positive")
    if args.output.exists():
        parser.error("Output exists; preserve first marker scan")
    duration, shift, geometry, panel_observations, samples, ends, changes = scan(
        args.video, args.step_s)
    result = {
        "status": "development_broadcast_graphic_evidence_not_physical_end_boundaries",
        "video_path": str(args.video),
        "video_sha256": digest(args.video),
        "reader_sha256": digest(ROOT / "prototype/scoreboard_end_marker.py"),
        "runner_sha256": digest(Path(__file__)),
        "video_duration_s": duration,
        "calibrated_horizontal_shift_px": shift,
        "calibrated_header_geometry": geometry,
        "panel_calibration_observations": panel_observations,
        "sample_step_s": args.step_s,
        "sample_count": len(samples),
        "recognized_count": sum(row["marker"] is not None for row in samples),
        "ends": ends,
        "observed_marker_changes": changes,
        "samples": samples,
        "limitations": [
            "The China frame at 500 s supplied the frozen arrow template and threshold development.",
            "A broadcast graphic can lag physical play and can be occluded; marker changes are not throw or end-boundary timestamps.",
            "No unobserved end is inserted when the graphic is absent or unreadable.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"video": args.video.name, "shift_px": shift,
                      "header_geometry": geometry,
                      "recognized": result["recognized_count"],
                      "sample_count": len(samples), "ends": [row["end"] for row in ends],
                      "changes": changes}))


if __name__ == "__main__":
    main()
