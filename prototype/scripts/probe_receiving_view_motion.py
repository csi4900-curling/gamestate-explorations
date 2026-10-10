"""Inspect same-colour stone-cap motion in the second 2024 broadcast view.

Development diagnostic only: an unobserved receiving stone is not evidence
that no throw occurred. This deliberately retains every visual track.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from throw_detection import PassageConfig, stone_candidates
from scene_cuts import scene_cut_evidence


RIGHT_ROI = (325, 110, 635, 355)


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def associate_tracks(observations, cut_times_s=(), *, max_gap_s=0.5, max_step_px=22):
    tracks = []
    cuts = set(cut_times_s)
    for t, candidates in observations:
        live = [] if t in cuts else [
            i for i, track in enumerate(tracks) if t - track[-1]["time_s"] <= max_gap_s
        ]
        costs = np.full((len(live), len(candidates)), 1e6)
        for row, index in enumerate(live):
            last = tracks[index][-1]
            for col, candidate in enumerate(candidates):
                if candidate["colour"] != last["colour"]:
                    continue
                distance = np.linalg.norm(np.subtract(last["pixel"], candidate["pixel"]))
                if distance <= max_step_px:
                    costs[row, col] = distance
        matched = set()
        if costs.size:
            rows, cols = linear_sum_assignment(costs)
            for row, col in zip(rows, cols):
                if costs[row, col] >= 1e6:
                    continue
                tracks[live[row]].append({**candidates[col], "time_s": t})
                matched.add(col)
        for col, candidate in enumerate(candidates):
            if col not in matched:
                tracks.append([{**candidate, "time_s": t}])
    return tracks


def summarize(track):
    points = np.asarray([row["pixel"] for row in track], dtype=float)
    displacement = float(np.linalg.norm(points[-1] - points[0]))
    path = float(np.sum(np.linalg.norm(np.diff(points, axis=0), axis=1)))
    return {
        "colour": track[0]["colour"],
        "first_s": track[0]["time_s"],
        "last_s": track[-1]["time_s"],
        "observations": len(track),
        "start_pixel": track[0]["pixel"],
        "end_pixel": track[-1]["pixel"],
        "displacement_px": round(displacement, 3),
        "path_px": round(path, 3),
        "median_bbox_width_px": float(np.median([row["bbox"][2] for row in track])),
        "median_body_support": round(float(np.median([row["body_support"] for row in track])), 3),
    }


def scan_window(cap, fps, config, start, end):
    observations = []
    hard_cuts = []
    previous_right = None
    for t in np.arange(start, end, 0.1):
        cap.set(cv2.CAP_PROP_POS_FRAMES, round(float(t) * fps))
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"Decode failed at {t}")
        sample_time = round(float(t), 3)
        right = frame[:, frame.shape[1] // 2 :]
        if previous_right is not None and scene_cut_evidence(previous_right, right)["hard_cut"]:
            hard_cuts.append(sample_time)
        previous_right = right
        observations.append((sample_time, stone_candidates(frame, config)))
    tracks = [summarize(track) for track in associate_tracks(observations, hard_cuts) if len(track) >= 5]
    return tracks, hard_cuts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--timeline", required=True, type=Path)
    parser.add_argument("--event-id", required=True, action="append")
    parser.add_argument("--shared-window", action="store_true",
                        help="Also track continuously from the first event to the last")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    timeline = json.loads(args.timeline.read_text())
    if sha256(args.video) != timeline["source_sha256"]:
        parser.error("Video does not match timeline source hash")
    by_id = {row["id"]: row for row in timeline["observed_events"]}
    if len(args.event_id) != len(set(args.event_id)) or any(e not in by_id for e in args.event_id):
        parser.error("Event IDs must be unique and present in timeline")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened() or fps <= 0:
        raise RuntimeError("Cannot decode source")
    config = PassageConfig(roi=RIGHT_ROI)
    results = []
    for event_id in args.event_id:
        event = by_id[event_id]
        crossing = event["crossing_time_s"]
        start = max(0.0, crossing - 2.0)
        end = min(cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps, crossing + 12.0)
        tracks, hard_cuts = scan_window(cap, fps, config, start, end)
        tracks.sort(key=lambda row: (row["colour"] != event["colour"], -row["displacement_px"]))
        results.append({
            "event_id": event_id,
            "colour": event["colour"],
            "crossing_time_s": crossing,
            "window_s": [round(start, 3), round(end, 3)],
            "hard_cut_times_s": hard_cuts,
            "tracks": tracks,
        })
    shared = None
    if args.shared_window:
        start = max(0.0, min(by_id[event_id]["crossing_time_s"] for event_id in args.event_id) - 2.0)
        end = min(cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps,
                  max(by_id[event_id]["crossing_time_s"] for event_id in args.event_id) + 12.0)
        tracks, cuts = scan_window(cap, fps, config, start, end)
        shared = {
            "window_s": [round(start, 3), round(end, 3)],
            "hard_cut_times_s": cuts,
            "tracks": sorted(tracks, key=lambda row: -row["displacement_px"]),
        }
    cap.release()
    output = {
        "status": "prediction_targeted_development_diagnostic",
        "source_id": timeline["source_id"],
        "source_sha256": timeline["source_sha256"],
        "timeline_sha256": sha256(args.timeline),
        "runner_sha256": sha256(Path(__file__)),
        "normalized_frame_size": [640, 360],
        "right_roi": RIGHT_ROI,
        "sample_step_s": 0.1,
        "limitations": [
            "Second-view cap tracks are not confirmed stone identities or matched to a first-view track.",
            "Occlusion, camera cuts, missed caps and stationary stones can hide a real throw.",
            "Events were selected after prediction inspection, so this is not an F1 evaluation.",
        ],
        "events": results,
    }
    if shared is not None:
        output["shared_window"] = shared
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({row["event_id"]: len(row["tracks"]) for row in results}))


if __name__ == "__main__":
    main()
