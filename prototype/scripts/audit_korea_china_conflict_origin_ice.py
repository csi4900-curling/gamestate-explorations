"""Test whether the existing broad below-ice cue separates post-cut conflicts."""

from hashlib import sha256
import json
from pathlib import Path
import statistics
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.origin_release_ice_support import below_ice_fraction  # noqa: E402
from prototype.stone_motion_fallback import moving_cap_tracks, stone_cap_candidates  # noqa: E402

SOURCE = ROOT / "validation/throw-event-benchmark/paralympics-2022-korea-china/source.mp4"
SIDECAR = ROOT / "validation/throw-event-benchmark/paralympics-2022-korea-china/VISUAL-ONLY-POSTCUT.json"
OUTPUT = ROOT / "validation/throw-event-benchmark/paralympics-2022-korea-china/ORIGIN-ICE-CONFLICT-PROBE.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Origin-ice conflict probe already exists")
    sidecar = json.loads(SIDECAR.read_text())
    if digest(SOURCE) != sidecar["source_video_sha256"]:
        raise ValueError("Source video differs from colour sidecar")
    conflicts = [row for row in sidecar["rows"] if row["colour_relation"] == "conflict"]
    cap = cv2.VideoCapture(str(SOURCE))
    if not cap.isOpened():
        raise RuntimeError("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for candidate in conflicts:
            start, end = candidate["release_window_s"]
            observations = {colour: [] for colour in ("red", "yellow")}
            for tick in range(round(start * 5), round(end * 5)):
                time_s = round(tick / 5, 3)
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f"Frame decode failed at {time_s}")
                for colour in observations:
                    found = stone_cap_candidates(frame, colour,
                                                  allow_bright_body=True,
                                                  allow_large_caps=True)
                    for proposal in found:
                        proposal["below_ice_fraction"] = below_ice_fraction(
                            frame, proposal["pixel"])
                    observations[colour].append((time_s, found))
            tracks = []
            for colour, samples in observations.items():
                for index, track in enumerate(moving_cap_tracks(
                        samples, max_gap_s=1.6, max_step_px=130), 1):
                    points = track["points"]
                    ice = [point["below_ice_fraction"] for point in points
                           if point["below_ice_fraction"] is not None]
                    tracks.append({
                        "track_id": f"{candidate['shot_id']}-{colour[0].upper()}{index:02}",
                        "colour": colour,
                        "interval_s": [points[0]["time_s"], points[-1]["time_s"]],
                        "point_count": len(points),
                        "span_px": round(track["span_px"], 2),
                        "median_y_px": round(statistics.median(p["pixel"][1] for p in points), 2),
                        "median_below_ice_fraction": round(statistics.median(ice), 4) if ice else None,
                        "fraction_points_with_below_ice_at_least_0_6": round(
                            sum(value >= 0.6 for value in ice) / len(ice), 4) if ice else None,
                    })
            rows.append({
                "candidate_id": candidate["candidate_id"],
                "shot_id": candidate["shot_id"],
                "original_colour": candidate["original_colour"],
                "postcut_colour": candidate["postcut_colour"],
                "origin_tracks": tracks,
                "red_tracks_with_median_below_ice_at_least_0_6": sum(
                    row["colour"] == "red" and row["median_below_ice_fraction"] is not None
                    and row["median_below_ice_fraction"] >= 0.6 for row in tracks),
            })
    finally:
        cap.release()
    result = {
        "status": "postscore_ice_context_counterexample_not_stone_identity_validation",
        "source_video_sha256": digest(SOURCE),
        "colour_sidecar_sha256": digest(SIDECAR),
        "cap_tracker_code_sha256": digest(ROOT / "prototype/stone_motion_fallback.py"),
        "ice_code_sha256": digest(ROOT / "prototype/origin_release_ice_support.py"),
        "runner_sha256": digest(Path(__file__)),
        "selected_conflict_count": len(rows),
        "conflicts_retaining_high_ice_red_track_count": sum(
            row["red_tracks_with_median_below_ice_at_least_0_6"] > 0 for row in rows),
        "rows": rows,
        "limitations": [
            "The four cases were selected after the first transfer from post-cut colour conflicts.",
            "White ice below a coloured patch does not identify a stone; player clothing and equipment can share this context.",
            "Neither origin nor receiving tracks establish physical cross-view stone identity.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print({"conflicts": len(rows), "retain_high_ice_red_track":
           result["conflicts_retaining_high_ice_red_track_count"]})


if __name__ == "__main__":
    main()
