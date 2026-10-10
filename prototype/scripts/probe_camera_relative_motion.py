"""Measure camera-compensated motion of specified raw visual tracks."""

import argparse
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from camera_relative_motion import longest_relative_motion_run, sample_track_camera_motion


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--learned-raw", type=Path, required=True)
    parser.add_argument("--cap-raw", type=Path, required=True)
    parser.add_argument("--candidate-id", action="append", required=True,
                        help="Prefix an ID with learned: or cap:")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve earlier diagnostic")
    sources = {
        "learned": json.loads(args.learned_raw.read_text()),
        "cap": json.loads(args.cap_raw.read_text()),
    }
    digest = file_sha256(args.video)
    if any(row["source_sha256"] != digest for row in sources.values()):
        parser.error("Visual artifacts differ from video fingerprint")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if digest == reserved["source_sha256"]:
        parser.error("Reserved independent source cannot be used for development")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        parser.error("Unreadable video")
    cache = {}

    def frame_at(time_s):
        if time_s not in cache:
            cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Frame decode failed at {time_s} s")
            cache[time_s] = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
        return cache[time_s]

    rows = []
    for qualified_id in args.candidate_id:
        kind, separator, candidate_id = qualified_id.partition(":")
        if not separator or kind not in sources:
            parser.error(f"Use learned:ID or cap:ID: {qualified_id}")
        candidates = [row for row in sources[kind]["motion_candidates"]
                      if row["id"] == candidate_id]
        if len(candidates) != 1:
            parser.error(f"Candidate ID absent or duplicated: {qualified_id}")
        candidate = candidates[0]
        pair_rows = sample_track_camera_motion(candidate["visual_track_points"], frame_at)
        rows.append({
            "qualified_id": qualified_id,
            "colour": candidate["colour"],
            "evidence_interval_s": candidate["evidence_interval_s"],
            "pair_count": len(pair_rows),
            "reliable_pair_count": sum(row["registration_reliable"] for row in pair_rows),
            "reliable_moving_pair_count": sum(
                row["camera_residual_px"] is not None and row["camera_residual_px"] > 5
                for row in pair_rows
            ),
            "longest_relative_motion_run": longest_relative_motion_run(pair_rows),
            "pairs": pair_rows,
        })
    cap.release()
    result = {
        "status": "development_camera_relative_track_motion_probe",
        "source_id": sources["learned"]["source_id"],
        "source_sha256": digest,
        "source_interval_s": sources["learned"]["source_interval_s"],
        "learned_raw_sha256": file_sha256(args.learned_raw),
        "cap_raw_sha256": file_sha256(args.cap_raw),
        "model_sha256": file_sha256(ROOT / "prototype/camera_relative_motion.py"),
        "runner_sha256": file_sha256(__file__),
        "pairs_approximately_s": 1,
        "registration_min_inliers": 30,
        "registration_min_inlier_fraction": 0.25,
        "moving_residual_threshold_px": 5,
        "tracks": rows,
        "limitations": [
            "Registration may follow players rather than the rink when static features are scarce.",
            "A camera cut or tracker identity switch can create spurious residual motion.",
            "Real movement relative to ice does not prove a delivered stone; players and displaced stones move too.",
            "This diagnostic does not promote or reject throw events.",
        ],
    }
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps([{key: row[key] for key in
                       ("qualified_id", "reliable_pair_count", "reliable_moving_pair_count",
                        "longest_relative_motion_run")}
                      for row in rows], indent=2))


if __name__ == "__main__":
    main()
