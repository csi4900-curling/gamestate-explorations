"""Postscore direction-agnostic image-motion episodes on three exposed clips.

This repairs the interpretation layer only; it does not change first-pass
detector results, certify a throw, or use left candidates to make detections.
"""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from sampled_motion_episode import sustained_motion_episode
from scripts.continue_yellow_by_contour import continue_path

BASE = ROOT / "validation/throw-event-benchmark"
SOURCES = {
    "korea": (
        BASE / "canada-korea-2024/yellow-handoff-generic-regression.json",
        BASE / "canada-korea-2024/yellow-contour-continuation-development.json",
    ),
    "slovakia": (
        BASE / "canada-slovakia-2024/yellow-handoff-1990-2070-development.json",
        BASE / "canada-slovakia-2024/yellow-contour-continuation-development.json",
    ),
    "estonia": (BASE / "canada-estonia-2024/yellow-contour-1720-1800-first-transfer.json", None),
}
LEFT_ESTONIA_S02 = BASE / "canada-estonia-2024/left-bound-full-interval/s02-paired.json"
OUT = BASE / "layout-router/full-2024-coverage/yellow-bidirectional-motion-episodes-postscore.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise SystemExit("Output exists; preserve first postscore episode audit")
    rows = []
    input_hashes = {}
    for name, (first_path, contour_path) in SOURCES.items():
        first = json.loads(first_path.read_text())
        input_hashes[name] = {"first_pass_sha256": digest(first_path)}
        if contour_path is not None:
            contour = json.loads(contour_path.read_text())
            if contour["target_video_sha256"] != first["target_video_sha256"]:
                raise ValueError(f"Source mismatch: {name}")
            contour_rows = contour["rows_with_contours"]
            input_hashes[name]["contour_scan_sha256"] = digest(contour_path)
        else:
            contour_rows = first["contour_rows_with_points"]
        for path in first["body_image_paths"]:
            episode = sustained_motion_episode(path["points"])
            if episode is None:
                rows.append(
                    {
                        "source": name,
                        "body_path_id": path["diagnostic_path_id"],
                        "motion_episode": None,
                        "continuation": None,
                    }
                )
                continue
            start = episode["path_suffix_start_index"]
            suffix = path["points"][start:]
            seed = {
                "diagnostic_path_id": path["diagnostic_path_id"],
                "first_observed_s": suffix[0]["time_s"],
                "last_observed_s": suffix[-1]["time_s"],
                "points": suffix,
            }
            joined = continue_path(seed, contour_rows)
            rows.append(
                {
                    "source": name,
                    "body_path_id": path["diagnostic_path_id"],
                    "original_body_path_interval_s": [
                        path["first_observed_s"],
                        path["last_observed_s"],
                    ],
                    "motion_episode": episode,
                    "continuation": joined,
                }
            )
    left = json.loads(LEFT_ESTONIA_S02.read_text())
    estonia = next(r for r in rows if r["source"] == "estonia" and r["motion_episode"])
    if (
        left["colour"] != "yellow"
        or left["source_sha256"]
        != json.loads(SOURCES["estonia"][0].read_text())["target_video_sha256"]
    ):
        raise ValueError("Estonia left candidate source mismatch")
    result = {
        "status": "postscore_bidirectional_image_motion_episodes_not_throw_truth",
        "input_sha256": input_hashes,
        "estonia_left_candidate_sha256": digest(LEFT_ESTONIA_S02),
        "episode_code_sha256": digest(ROOT / "prototype/sampled_motion_episode.py"),
        "continuation_code_sha256": digest(
            ROOT / "prototype/scripts/continue_yellow_by_contour.py"
        ),
        "runner_sha256": digest(Path(__file__)),
        "minimum_axis_step_1080p_px_per_s": 20,
        "minimum_consecutive_steps": 2,
        "minimum_axis_span_1080p_px": 75,
        "rows": rows,
        "estonia_s02_temporal_context": {
            "candidate_id": left["candidate_id"],
            "colour": left["colour"],
            "left_crossing_time_s": left["crossing_time_s"],
            "right_moving_run_last_observed_s": estonia["motion_episode"]["moving_run_interval_s"][
                1
            ],
            "crossing_after_right_last_observation_s": round(
                left["crossing_time_s"] - estonia["motion_episode"]["moving_run_interval_s"][1], 3
            ),
            "physical_same_stone_link_verified": False,
        },
        "limitations": [
            "This is a postresult repair fitted after inspecting Estonia's downward-moving path.",
            "A stationary-to-motion transition in one linked path can be a track identity switch.",
            "The left S02 candidate is attached only as temporal context, never used for detection.",
            "An image-motion onset bracket is not physical release, and no stop exists for Estonia before the view ends.",
            "None of these three selected clips establishes complete-video throw F1 or game-state correctness.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            [
                (
                    r["source"],
                    r["motion_episode"]["direction"] if r["motion_episode"] else None,
                    r["motion_episode"]["motion_onset_observation_bracket_s"]
                    if r["motion_episode"]
                    else None,
                    r["continuation"]["image_motion_interpretation"]["visual_stop_bracket_s"]
                    if r["continuation"]
                    else None,
                )
                for r in rows
            ]
        )
    )


if __name__ == "__main__":
    main()
