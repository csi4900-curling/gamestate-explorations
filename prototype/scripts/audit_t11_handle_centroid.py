"""Test whether a simple handle-mask centroid can stand in for spin phase.

The mask is normalized for apparent size and location. This is a diagnostic
against a settled-stone control, not an angular-orientation estimator.
"""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from probe_t11_handle_periodicity import mask_series  # noqa: E402

VIDEO = ROOT / "prototype/throw-analysis/end3.mp4"
SOURCE = ROOT / "prototype/throw-analysis/source.json"
TRACK = ROOT / "prototype/cross-view/results.json"
OUTPUT = ROOT / "validation/spin-observability/T11-handle-centroid-control.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def measure(masks, times):
    rows = []
    for mask, time_s in zip(masks, times):
        # These are the same normalized handle rows used by the polarity pilot.
        ys, xs = np.where(mask[18:35, :] > 0)
        rows.append({"time_s": time_s,
                     "centroid_offset_px": round(float(xs.mean() - 40), 3) if len(xs) else None,
                     "handle_mask_pixels": int(len(xs))})
    values = np.array([r["centroid_offset_px"] for r in rows], dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Missing handle-mask centroid")
    return rows, {
        "sample_count": len(rows),
        "offset_range_px": round(float(np.ptp(values)), 3),
        "median_adjacent_change_px": round(float(np.median(np.abs(np.diff(values)))), 3),
        "maximum_adjacent_change_px": round(float(np.max(np.abs(np.diff(values)))), 3),
    }


def main():
    if OUTPUT.exists():
        raise SystemExit("Centroid-control artifact already exists")
    metadata = json.loads(SOURCE.read_text())
    track = json.loads(TRACK.read_text())
    throw = next(row for row in track["throws"] if row["id"] == "T11")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Cannot open source clip")
    windows = (("moving", 2307.0, 2312.5, False),
               ("settled_control", 2319.5, 2323.0, True))
    observations = {}
    try:
        for name, start, end, settled in windows:
            times = np.round(np.arange(start, end + 0.001, 0.1), 3)
            masks, retained = mask_series(
                cap, throw, times, metadata["source_interval_s"][0],
                settled=settled)
            if len(retained) != len(times):
                raise RuntimeError(f"Missing {name} masks")
            rows, summary = measure(masks, retained)
            observations[name] = {"summary": summary, "rows": rows}
    finally:
        cap.release()
    result = {
        "status": "diagnostic_centroid_is_not_calibrated_spin_phase",
        "source_video_sha256": digest(VIDEO),
        "source_metadata_sha256": digest(SOURCE),
        "track_sha256": digest(TRACK),
        "mask_extraction_sha256": digest(
            ROOT / "prototype/scripts/probe_t11_handle_periodicity.py"),
        "runner_sha256": digest(Path(__file__)),
        "sample_rate_hz": 10,
        "normalized_mask_rows": [18, 35],
        "observations": observations,
        "interpretation": (
            "Horizontal centroid is affected by silhouette, size normalization "
            "and image changes even for the settled control. No angle, turn "
            "direction or revolution count follows from this cue."),
    }
    with OUTPUT.open("x") as f:
        f.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: v["summary"] for k, v in observations.items()}, indent=2))


if __name__ == "__main__":
    main()
