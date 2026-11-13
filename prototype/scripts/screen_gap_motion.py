"""Screen Beijing visual gap tracks by ice scene and motion episode."""

import argparse
import json
from pathlib import Path
import statistics
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from gap_scene_confirmation import confirm_gap_episodes, ice_scene_fraction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve earlier screen")
    source = json.loads(args.candidates.read_text())
    digest = file_sha256(args.video)
    if digest != source["source_sha256"]:
        parser.error("Video fingerprint differs from candidate artifact")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if digest == reserved["source_sha256"]:
        parser.error("This source is reserved for independent evaluation")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        raise ValueError("Unreadable video")
    cache = {}
    context = []
    for candidate in source["motion_candidates"]:
        fractions = []
        for point in candidate["visual_track_points"]:
            t = point["time_s"]
            if t not in cache:
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
                ok, frame = cap.read()
                if not ok:
                    cap.release()
                    raise RuntimeError(f"Frame decode failed at {t} s")
                cache[t] = ice_scene_fraction(frame)
            fractions.append(cache[t])
        context.append(
            {
                "id": candidate["id"],
                "median_ice_scene_fraction": round(statistics.median(fractions), 5),
                "sampled_times_s": [point["time_s"] for point in candidate["visual_track_points"]],
            }
        )
    cap.release()
    decisions = confirm_gap_episodes(source["motion_candidates"], context)
    accepted = {row["id"] for row in decisions if row["status"] == "corroborated_gap_candidate"}
    result = {
        "status": "development_gap_scene_episode_screen",
        "source_id": source["source_id"],
        "source_sha256": digest,
        "source_interval_s": source["source_interval_s"],
        "input_sha256": file_sha256(args.candidates),
        "model_sha256": file_sha256(ROOT / "prototype/gap_scene_confirmation.py"),
        "runner_sha256": file_sha256(__file__),
        "context": context,
        "decisions": decisions,
        "corroborated_candidates": [
            item for item in source["motion_candidates"] if item["id"] in accepted
        ],
        "withheld_candidates": [
            item for item in source["motion_candidates"] if item["id"] not in accepted
        ],
        "limitations": [
            "Ice fraction and episode grouping were chosen after inspecting Canada–China and Sweden–Switzerland gaps.",
            "Corroborated candidates are not promoted to confirmed timeline events without separate validation.",
            "Camera motion, a second delivery close in time or moving displaced stones can defeat this rule.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "corroborated": len(result["corroborated_candidates"]),
                "withheld": len(result["withheld_candidates"]),
            }
        )
    )


if __name__ == "__main__":
    main()
