"""Postscore audit of a frozen cap-patch classifier on conflicting origin tracks.

This selected-case audit is diagnostic only. It never edits the first-pass
event ledger or interprets a patch score as proof of a physical throw.
"""

from hashlib import sha256
import json
from pathlib import Path
import statistics
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cap_patch_verifier import score_candidates  # noqa: E402
from stone_motion_fallback import moving_cap_tracks, stone_cap_candidates  # noqa: E402

BASE = ROOT / "validation/throw-event-benchmark/paralympics-2022-korea-china"
SOURCE = BASE / "source.mp4"
SIDECAR = BASE / "VISUAL-ONLY-POSTCUT.json"
MODEL = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1/model-excluding-china-dev.npz"
OUTPUT = BASE / "ORIGIN-CAP-PATCH-CONFLICT-PROBE.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Selected-case patch audit already exists")
    sidecar = json.loads(SIDECAR.read_text())
    if digest(SOURCE) != sidecar["source_video_sha256"]:
        raise ValueError("Source video differs from frozen colour sidecar")
    model = np.load(MODEL)
    conflicts = [row for row in sidecar["rows"] if row["colour_relation"] == "conflict"]
    cap = cv2.VideoCapture(str(SOURCE), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for case in conflicts:
            start, end = case["release_window_s"]
            observations = {colour: [] for colour in ("red", "yellow")}
            for tick in range(round(start * 5), round(end * 5)):
                time_s = round(tick / 5, 3)
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f"Frame decode failed at {time_s}")
                for colour in observations:
                    proposals = stone_cap_candidates(frame, colour,
                                                     allow_bright_body=True,
                                                     allow_large_caps=True)
                    scored = score_candidates(frame, proposals, model)
                    observations[colour].append((time_s, scored))
            tracks = []
            for colour, samples in observations.items():
                for index, track in enumerate(moving_cap_tracks(
                        samples, max_gap_s=1.6, max_step_px=130), 1):
                    points = track["points"]
                    scores = [float(point["patch_score"]) for point in points]
                    tracks.append({
                        "track_id": f"{case['shot_id']}-{colour[0].upper()}{index:02}",
                        "colour": colour,
                        "interval_s": [points[0]["time_s"], points[-1]["time_s"]],
                        "point_count": len(points),
                        "span_px": round(track["span_px"], 2),
                        "median_patch_score": round(statistics.median(scores), 5),
                        "accepted_point_fraction": round(sum(score >= 0 for score in scores)
                                                         / len(scores), 4),
                    })
            red = [track for track in tracks if track["colour"] == "red"]
            rows.append({
                "candidate_id": case["candidate_id"],
                "shot_id": case["shot_id"],
                "original_colour": case["original_colour"],
                "postcut_colour": case["postcut_colour"],
                "red_track_count": len(red),
                "red_tracks_median_patch_accepted": sum(
                    track["median_patch_score"] >= 0 for track in red),
                "tracks": tracks,
            })
    finally:
        cap.release()
    result = {
        "status": "postscore_selected_conflict_patch_identity_audit_not_event_validation",
        "source_video_sha256": digest(SOURCE),
        "colour_sidecar_sha256": digest(SIDECAR),
        "model_sha256": digest(MODEL),
        "cap_tracker_code_sha256": digest(ROOT / "prototype/stone_motion_fallback.py"),
        "patch_verifier_code_sha256": digest(ROOT / "prototype/cap_patch_verifier.py"),
        "runner_sha256": digest(Path(__file__)),
        "selected_conflict_count": len(rows),
        "conflicts_retaining_accepted_red_track_count": sum(
            row["red_tracks_median_patch_accepted"] > 0 for row in rows),
        "rows": rows,
        "limitations": [
            "The four windows were selected after first-pass colour conflicts, not sampled independently.",
            "The patch classifier labels stone-like appearance, not movement, release or cross-view identity.",
            "A track median score is a diagnostic; no event candidate is accepted or rejected here.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print({"conflicts": len(rows), "retaining_accepted_red_track":
           result["conflicts_retaining_accepted_red_track_count"]})


if __name__ == "__main__":
    main()
