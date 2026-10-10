"""Development probe: five-hertz small/large coloured-cap motion tracks."""

import argparse
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from gap_motion_candidates import candidates_from_observations
from stone_motion_fallback import stone_cap_candidates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--gap-id", required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve earlier probe")
    if args.start < 0 or args.end <= args.start:
        parser.error("Invalid interval")
    digest = file_sha256(args.video)
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if digest == reserved["source_sha256"]:
        parser.error("Reserved independent source cannot be used for development")
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    duration = capture.get(cv2.CAP_PROP_FRAME_COUNT) / fps if fps > 0 else 0
    if args.end > duration:
        capture.release()
        parser.error("Interval exceeds readable video")
    observations = {"red": [], "yellow": []}
    for step in range(args.start * 5, args.end * 5):
        t = round(step / 5, 1)
        capture.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
        ok, frame = capture.read()
        if not ok:
            capture.release()
            raise RuntimeError(f"Frame decode failed at {t} s")
        for colour in observations:
            observations[colour].append(
                (
                    t,
                    stone_cap_candidates(
                        frame, colour, allow_bright_body=True, allow_large_caps=True
                    ),
                )
            )
    capture.release()
    candidates = candidates_from_observations(
        observations,
        args.gap_id,
        [args.start, args.end],
        tracker_max_gap_s=1.6,
        tracker_max_step_px=130,
    )
    result = {
        "status": "development_multiscale_cap_gap_motion_probe",
        "source_id": args.source_id,
        "source_sha256": digest,
        "source_interval_s": [args.start, args.end],
        "scanned_gaps": [
            {"id": args.gap_id, "interval_s": [args.start, args.end],
             "samples": 5 * (args.end - args.start), "candidate_count": len(candidates)}
        ],
        "visual_code_sha256": file_sha256(ROOT / "prototype/stone_motion_fallback.py"),
        "candidate_code_sha256": file_sha256(ROOT / "prototype/gap_motion_candidates.py"),
        "runner_sha256": file_sha256(__file__),
        "sample_period_s": 0.2,
        "tracker_max_gap_s": 1.6,
        "tracker_max_step_px_s": 130,
        "motion_candidates": candidates,
        "candidate_count": len(candidates),
        "limitations": [
            "Cap-only boxes can include colour graphics or players and do not locate the whole stone.",
            "Greedy tracking may merge identities across camera cuts or collisions.",
            "Every output remains an unconfirmed candidate, not a throw event.",
        ],
    }
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"samples": 5 * (args.end - args.start), "motion_candidates": len(candidates)}))


if __name__ == "__main__":
    main()
