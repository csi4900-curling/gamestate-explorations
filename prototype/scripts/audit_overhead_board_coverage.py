"""Measure image bounds around every event-gated overhead board observation.

This source-only geometric audit is deliberately optimistic: image bounds
cannot account for rink-edge cropping, occlusions, or non-stone objects. A
failed envelope proves missing visual coverage; a passed envelope does not
prove that every stone was seen.
"""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.scripts.scan_china_full_match_boards import read_frame
from prototype.video_board_observation_v2 import detect_overhead_house

BASE = ROOT / "validation/official-shot-sequence"
JOBS = (
    (
        "china",
        BASE / "china-full-match-event-gated-source-video-boards-first.json",
        ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4",
    ),
    (
        "norway_end2",
        BASE / "norway-end2-event-gated-source-video-boards-first.json",
        ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4",
    ),
)
OUTPUT = BASE / "event-gated-overhead-image-coverage-first.json"
# Diagnostic rectangles in detected house-radius units, not claims about
# the official in-play boundary. The longer one represents a guard-zone view.
ENVELOPES = {
    "house": {"lateral": [-1.0, 1.0], "longitudinal": [-1.0, 1.0]},
    "extended": {"lateral": [-1.25, 1.25], "longitudinal": [-3.0, 1.0]},
}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def visible_bounds(house, side, width=640, height=360):
    """Axis-aligned image-bound rectangle in scan-normalized coordinates."""
    cx, cy = house["center_px"]
    radius = house["outer_radius_px"]
    sign = 1 if side == "top" else -1
    lateral = sorted((sign * (0 - cx) / radius, sign * ((width - 1) - cx) / radius))
    longitudinal = sorted((sign * (0 - cy) / radius, sign * ((height - 1) - cy) / radius))
    return {
        "lateral": [round(v, 3) for v in lateral],
        "longitudinal": [round(v, 3) for v in longitudinal],
    }


def contains(bounds, envelope):
    return all(
        bounds[axis][0] <= limits[0] and bounds[axis][1] >= limits[1]
        for axis, limits in envelope.items()
    )


def audit_recording(name, scan_path, video_path):
    scan = json.loads(scan_path.read_text())
    if scan["source_video_sha256"] != digest(video_path):
        raise ValueError(f"{name} source-video provenance mismatch")
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for row in scan["rows"]:
            if not row["stable_partial_board"]:
                continue
            side = row.get("local_inferred_delivery_side") or scan.get("inferred_delivery_side")
            if side not in ("top", "bottom"):
                raise ValueError(f"{name} {row['counter_id']}: no coordinate orientation")
            frames = []
            for time_s in row["sampled_times_s"]:
                frame = read_frame(cap, fps, time_s)
                if frame is None:
                    continue
                house = detect_overhead_house(frame)
                if house is None or (house["delivery_side"] not in ("uncertain", side)):
                    continue
                bounds = visible_bounds(house, side)
                frames.append(
                    {
                        "time_s": time_s,
                        "house_center_px": house["center_px"],
                        "detected_house_radius_px": house["outer_radius_px"],
                        "image_bounds_house_radii": bounds,
                        "envelope_visible_in_image": {
                            key: contains(bounds, envelope) for key, envelope in ENVELOPES.items()
                        },
                    }
                )
            rows.append(
                {
                    "counter_id": row["counter_id"],
                    "stable_stone_count": len(row["stable_partial_board"]),
                    "orientation": side,
                    "accepted_overhead_frame_count": len(frames),
                    "any_frame_house_envelope": any(
                        f["envelope_visible_in_image"]["house"] for f in frames
                    ),
                    "any_frame_extended_envelope": any(
                        f["envelope_visible_in_image"]["extended"] for f in frames
                    ),
                    "frames": frames,
                }
            )
    finally:
        cap.release()
    return {
        "recording": name,
        "scan_sha256": digest(scan_path),
        "source_video_sha256": digest(video_path),
        "board_count": len(rows),
        "house_envelope_image_count": sum(r["any_frame_house_envelope"] for r in rows),
        "extended_envelope_image_count": sum(r["any_frame_extended_envelope"] for r in rows),
        "rows": rows,
    }


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first image-coverage audit")
    records = [audit_recording(*job) for job in JOBS]
    result = {
        "status": "source_video_image_bounds_audit_no_official_positions",
        "envelopes_house_radii": ENVELOPES,
        "house_detector_sha256": digest(ROOT / "prototype/video_board_observation_v2.py"),
        "runner_sha256": digest(Path(__file__)),
        "recordings": records,
        "limitations": [
            "These are upper bounds from the rectangular image, not verified visible ice extents.",
            "Occlusions, rink edges, and unobserved camera cuts may reduce actual coverage.",
            "The extended rectangle is a diagnostic envelope, not an official in-play ruling.",
            "No official board positions or shot outcomes were read.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        [
            {
                key: record[key]
                for key in (
                    "recording",
                    "board_count",
                    "house_envelope_image_count",
                    "extended_envelope_image_count",
                )
            }
            for record in records
        ]
    )


if __name__ == "__main__":
    main()
