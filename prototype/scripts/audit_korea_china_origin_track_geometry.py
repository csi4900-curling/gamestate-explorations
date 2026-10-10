"""Compare image-space cap-track geometry in colour conflicts and controls.

This is a selected postscore diagnostic, not a physical-stone classifier.
"""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from stone_motion_fallback import moving_cap_tracks, stone_cap_candidates  # noqa: E402

BASE = ROOT / "validation/throw-event-benchmark/paralympics-2022-korea-china"
SOURCE = BASE / "source.mp4"
LEDGER = ROOT / "validation/curlobserver-learned-probe/korea-china-full-first-transfer/candidate-event-ledger.json"
OUTPUT = BASE / "ORIGIN-TRACK-GEOMETRY-PILOT.json"
CONFLICT_IDS = ("T001", "T095", "T099", "T101")
CONTROL_IDS = ("T002", "T004", "T006", "T008", "T010")


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def summarize(track, shot_id, colour, index):
    points = track["points"]
    xy = np.asarray([point["pixel"] for point in points], dtype=float)
    deltas = np.diff(xy, axis=0)
    length = float(np.linalg.norm(deltas, axis=1).sum())
    net = xy[-1] - xy[0]
    ystep = deltas[:, 1]
    signed_y = 1 if net[1] > 0 else -1 if net[1] < 0 else 0
    return {
        "track_id": f"{shot_id}-{colour[0].upper()}{index:02}",
        "colour": colour,
        "interval_s": [points[0]["time_s"], points[-1]["time_s"]],
        "point_count": len(points),
        "first_pixel": [round(float(v), 2) for v in xy[0]],
        "last_pixel": [round(float(v), 2) for v in xy[-1]],
        "net_delta_px": [round(float(v), 2) for v in net],
        "span_px": round(track["span_px"], 2),
        "path_length_px": round(length, 2),
        "net_to_path_ratio": round(float(np.linalg.norm(net) / length), 4)
        if length > 0 else None,
        "fraction_y_steps_in_net_direction": round(float(np.mean(ystep * signed_y > 0)), 4)
        if signed_y else None,
        "y_range_px": round(float(np.ptp(xy[:, 1])), 2),
    }


def main():
    if OUTPUT.exists():
        raise SystemExit("Origin geometry pilot already exists")
    ledger = json.loads(LEDGER.read_text())
    if digest(SOURCE) != ledger["source_sha256"]:
        raise ValueError("Source video differs from frozen ledger")
    by_id = {row["candidate_id"]: row for row in ledger["events"]}
    selected = [(cid, "postscore_colour_conflict" if cid in CONFLICT_IDS else
                 "counter_backed_red_control") for cid in CONFLICT_IDS + CONTROL_IDS]
    if len(by_id) != len(ledger["events"]) or any(cid not in by_id for cid, _ in selected):
        raise ValueError("Selected candidate missing or duplicate IDs")
    cap = cv2.VideoCapture(str(SOURCE), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for cid, selection in selected:
            candidate = by_id[cid]
            start, end = candidate["release_window_s"]
            observations = {colour: [] for colour in ("red", "yellow")}
            for tick in range(round(start * 5), round(end * 5)):
                time_s = round(tick / 5, 3)
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f"Frame decode failed at {time_s}")
                for colour in observations:
                    observations[colour].append((time_s, stone_cap_candidates(
                        frame, colour, allow_bright_body=True, allow_large_caps=True)))
            tracks = []
            for colour, samples in observations.items():
                for index, track in enumerate(moving_cap_tracks(
                        samples, max_gap_s=1.6, max_step_px=130), 1):
                    tracks.append(summarize(track, candidate["shot_id"], colour, index))
            rows.append({"candidate_id": cid, "selection": selection,
                         "shot_id": candidate["shot_id"],
                         "candidate_colour": candidate["colour"],
                         "counter_id": candidate["counter_id"], "tracks": tracks})
    finally:
        cap.release()
    result = {
        "status": "selected_postscore_image_space_track_geometry_not_stone_identity",
        "source_video_sha256": digest(SOURCE),
        "frozen_candidate_ledger_sha256": digest(LEDGER),
        "tracker_code_sha256": digest(ROOT / "prototype/stone_motion_fallback.py"),
        "runner_sha256": digest(Path(__file__)),
        "selection": {"conflicts": list(CONFLICT_IDS), "controls": list(CONTROL_IDS)},
        "rows": rows,
        "limitations": [
            "The cases were selected after the first transfer; controls are counter-backed candidate windows, not labelled stone tracks.",
            "Greedy colour-cap association can switch between objects, and an image-space direction depends on camera view.",
            "This audit supplies no event F1 or physical cross-view identity.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print([(row["candidate_id"], len(row["tracks"])) for row in rows])


if __name__ == "__main__":
    main()
