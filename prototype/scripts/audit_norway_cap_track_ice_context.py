"""Measure source-pixel ice context for every Norway cap-continuation seed."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.right_track_ice_context import nonice_ring_fraction  # noqa: E402
from prototype.right_track_underpoint_context import (  # noqa: E402
    underpoint_nonice_fraction,
)

BASE = ROOT / "validation"
VIDEO = BASE / "throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
TRANSFER = BASE / "official-shot-sequence/norway-2022-cap-area-gate-transfer-development.json"
OUT = BASE / "official-shot-sequence/norway-cap-track-ice-context-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Norway ice-context audit already exists")
    transfer = json.loads(TRANSFER.read_text())
    if transfer["source_video_sha256"] != digest(VIDEO):
        raise ValueError("Source/transfer hashes differ")
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        raise ValueError("Source video unreadable")
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for seed in transfer["rows"]:
            samples = []
            for point in seed["last_two_reconstructed_points_360"]:
                frame_index = round(point["time_s"] * fps)
                capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                ok, frame = capture.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise ValueError(f"Frame missing at {frame_index}")
                ring = nonice_ring_fraction(frame, point["pixel"])
                under = underpoint_nonice_fraction(frame, point["pixel"])
                samples.append({
                    "time_s": point["time_s"],
                    "decoded_frame_index": frame_index,
                    "cap_center_px_360": point["pixel"],
                    "nonice_ring_fraction": round(ring, 4),
                    "underpoint_nonice_fraction": (
                        None if under is None else round(under, 4)),
                })
            rows.append({
                "episode_id": seed["episode_id"],
                "colour": seed["colour"],
                "samples": samples,
                "exploratory_both_rings_below_0p30": all(
                    sample["nonice_ring_fraction"] < 0.30
                    for sample in samples),
                "prior_area_next_step_status": (
                    "camera_shot_boundary" if seed["shot_boundary_abstention"]
                    else seed["past_cap_area_0p5_to_2_decision"]["status"]),
                "physical_stone_identity_verified": False,
            })
    finally:
        capture.release()
    if len(rows) != transfer["source_catalog_track_count"]:
        raise ValueError("Track coverage differs")
    counts = Counter((row["prior_area_next_step_status"],
                      row["exploratory_both_rings_below_0p30"])
                     for row in rows)
    result = {
        "status": "all_seed_source_pixel_ice_context_diagnostic_not_stone_truth",
        "source_video_sha256": transfer["source_video_sha256"],
        "transfer_sha256": digest(TRANSFER),
        "runner_sha256": digest(Path(__file__)),
        "ring_code_sha256": digest(ROOT / "prototype/right_track_ice_context.py"),
        "underpoint_code_sha256": digest(ROOT / "prototype/right_track_underpoint_context.py"),
        "track_count": len(rows),
        "method": "Two previously reconstructed terminal track points per seed; existing 28x40-pixel non-ice ring and below-point metrics on decoded 640x360 source; exploratory 0.30 threshold inspected after selected source cases.",
        "outcome_cross_tab": [
            {"prior_area_next_step_status": status,
             "both_rings_below_0p30": passes,
             "seed_count": count}
            for (status, passes), count in sorted(counts.items())],
        "rows": rows,
        "limitations": [
            "A ring threshold chosen after viewing three examples is post-hoc and cannot establish error rates.",
            "Ice-like clothing and sideline ice may pass; real stones near painted houses or players may fail.",
            "These are cap-track candidates, not independently labelled physical throws or stone identities.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"tracks": len(rows),
                      "outcome_cross_tab": result["outcome_cross_tab"]}))


if __name__ == "__main__":
    main()
