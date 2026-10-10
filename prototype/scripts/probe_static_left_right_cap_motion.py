"""Probe right-view coloured motion inside active static-left source intervals.

These are high-recall object-motion proposals, not delivered-stone events.
The 1 Hz, 2024-right-panel rules are fixed for the first Latvia/Italy replay.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from stone_motion_fallback import moving_cap_tracks
from scripts.audit_split_panel_freeze import normalized_split_frame


def digest(path):
    result = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def right_colour_proposals(frame):
    """Find small coloured blobs in the rink portion of the right panel."""
    if frame.shape[:2] != (360, 640):
        raise ValueError("Expected 640×360 broadcast source")
    hue, saturation, value = cv2.split(cv2.cvtColor(frame, cv2.COLOR_BGR2HSV))
    masks = (
        ("red", ((hue < 12) | (hue > 170)) & (saturation > 70) & (value > 45)),
        ("yellow", (hue > 16) & (hue < 43) & (saturation > 70) & (value > 65)),
    )
    result = {"red": [], "yellow": []}
    for colour, mask in masks:
        mask[:145] = False
        mask[325:] = False
        mask[:, :330] = False
        mask[:, 630:] = False
        contours, _ = cv2.findContours(
            mask.astype(np.uint8) * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        for contour in contours:
            x, y, width, height = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            if not (4 <= area <= 120 and 4 <= width <= 24 and 3 <= height <= 16):
                continue
            result[colour].append(
                {
                    "pixel": [x + width / 2, y + height / 2],
                    "bbox": [x, y, width, height],
                    "cap_area_px2": round(float(area), 2),
                }
            )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--overlay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    overlay = json.loads(args.overlay.read_text())
    video_hash = digest(args.video)
    if video_hash != overlay["source_sha256"]:
        parser.error("Video and overlay sources differ")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    intervals = []
    try:
        for region in overlay["newly_unsupported_intervals"]:
            start, stop = region["interval_s"]
            observations = {"red": [], "yellow": []}
            sample_count = 0
            for time_s in range(int(start), int(stop) + 1):
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f"Could not decode {time_s} s")
                proposals = right_colour_proposals(normalized_split_frame(frame))
                for colour in observations:
                    observations[colour].append((float(time_s), proposals[colour]))
                sample_count += 1
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
            for index, track in enumerate(tracks, 1):
                track["track_id"] = f"R{index:03d}"
            intervals.append(
                {
                    "interval_s": [start, stop],
                    "sample_count": sample_count,
                    "raw_proposal_count_by_colour": {
                        colour: sum(len(candidates) for _, candidates in samples)
                        for colour, samples in observations.items()
                    },
                    "moving_track_count": len(tracks),
                    "tracks": tracks,
                }
            )
    finally:
        cap.release()
    output = {
        "status": "development_right_panel_motion_proposals_not_throw_events",
        "source_sha256": video_hash,
        "overlay_sha256": digest(args.overlay),
        "tracker_code_sha256": digest(ROOT / "prototype/stone_motion_fallback.py"),
        "frame_normalization_code_sha256": digest(
            ROOT / "prototype/scripts/audit_split_panel_freeze.py"
        ),
        "runner_sha256": digest(Path(__file__)),
        "sample_period_s": 1,
        "right_roi_xyxy": [330, 145, 630, 325],
        "colour_contour_area_px2": [4, 120],
        "moving_track_rule": "Existing moving_cap_tracks: ≥4 points over ≥3 s, ≥25 px span, ≤2 s gap, ≤25 px/s nearest-step association.",
        "intervals": intervals,
        "limitations": [
            "Parameters were fixed for a first development replay after the static-left finding.",
            "A coloured blob can be a stone, player, equipment, graphic or compression artefact.",
            "Greedy image-space tracks can switch identities and do not prove delivery or settle time.",
            "No event decision or precision/recall/F1 is inferred from these proposals.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "intervals": len(intervals),
                "tracks": sum(row["moving_track_count"] for row in intervals),
            }
        )
    )


if __name__ == "__main__":
    main()
