"""Compare stationary versus track-following motion around each raw passage."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def gray_frame(cap, fps, seconds):
    cap.set(cv2.CAP_PROP_POS_FRAMES, round(seconds * fps))
    ok, image = cap.read()
    if not ok:
        raise RuntimeError(f"Could not decode {seconds:.3f} s")
    resized = cv2.resize(image, (640, 360), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)


def context_costs(before_image, after_image, before_xy, after_xy):
    before = cv2.getRectSubPix(before_image, (61, 61), tuple(map(float, before_xy))).astype(float)
    stationary = cv2.getRectSubPix(after_image, (61, 61), tuple(map(float, before_xy))).astype(
        float
    )
    moving = cv2.getRectSubPix(after_image, (61, 61), tuple(map(float, after_xy))).astype(float)
    yy, xx = np.ogrid[-30:31, -30:31]
    radius = np.sqrt(xx * xx + yy * yy)
    ring = (radius >= 12) & (radius <= 30)
    masks = {"full": ring, "upper": ring & (yy < 0), "lower": ring & (yy > 0)}
    results = {}
    for label, mask in masks.items():
        fixed_cost = float(np.mean(np.abs(before - stationary)[mask]))
        following_cost = float(np.mean(np.abs(before - moving)[mask]))
        results[label] = {
            "stationary_mae": fixed_cost,
            "track_following_mae": following_cost,
            "comovement_index": (fixed_cost - following_cost)
            / (fixed_cost + following_cost + 1e-6),
        }
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--tracks", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first diagnostic")
    tracks = json.loads(args.tracks.read_text())
    if digest(args.video) != tracks["source_sha256"]:
        parser.error("Video differs from track replay")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened() or fps <= 0:
        parser.error("Unreadable video")
    rows = []
    for track in tracks["tracks"]:
        t = track["crossing_time_s"]
        points = track["points"]
        before = min(points, key=lambda point: abs(point["time_s"] - (t - 0.25)))
        after = min(points, key=lambda point: abs(point["time_s"] - (t + 0.25)))
        elapsed = after["time_s"] - before["time_s"]
        travel = float(np.linalg.norm(np.subtract(after["pixel"], before["pixel"])))
        if elapsed < 0.2 or travel < 3:
            rows.append(
                {
                    "event_id": track["event_id"],
                    "status": "abstain_insufficient_observed_motion",
                    "sample_times_s": [before["time_s"], after["time_s"]],
                    "travel_px": travel,
                }
            )
            continue
        first = gray_frame(cap, fps, before["time_s"])
        second = gray_frame(cap, fps, after["time_s"])
        rows.append(
            {
                "event_id": track["event_id"],
                "status": "scored_surrounding_motion",
                "sample_times_s": [before["time_s"], after["time_s"]],
                "sample_positions_px": [before["pixel"], after["pixel"]],
                "travel_px": travel,
                "elapsed_s": elapsed,
                "context": context_costs(first, second, before["pixel"], after["pixel"]),
            }
        )
    cap.release()
    result = {
        "status": "postscore_candidate_context_motion_diagnostic_not_physical_verifier",
        "source_sha256": tracks["source_sha256"],
        "tracks_artifact_sha256": digest(args.tracks),
        "runner_sha256": digest(Path(__file__)),
        "context_ring_inner_radius_px": 12,
        "context_ring_outer_radius_px": 30,
        "target_offsets_from_crossing_s": [-0.25, 0.25],
        "interpretation": "Positive index means nearby pixels follow the track better; negative means they stay fixed in the image better.",
        "rows": rows,
        "limitations": [
            "The visible context can contain both ice and players, especially near a delivery.",
            "Camera movement or a cut can change the index independently of object identity.",
            "The probe uses only one frame pair per raw candidate and no independent event labels.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "scored": sum(row["status"] == "scored_surrounding_motion" for row in rows),
                "total": len(rows),
            }
        )
    )


if __name__ == "__main__":
    main()
