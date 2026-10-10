"""Join upward body-template paths to unpositioned side-view cap candidates.

This is a development image-space handoff, not a physical throw or stop label.
The runner never reads a T11 location track or source-only review coordinates.
"""

from hashlib import sha256
import json
from math import hypot
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from red_motion_window import split_moving_prefix

BASE = ROOT / "validation/throw-event-benchmark/canada-korea-2024"
BODY = BASE / "t11-score-roi-ablation-development.json"
CAP = BASE / "t11-sideview-cap-fullclip-development.json"
OUT = BASE / "t11-template-to-cap-handoff-development.json"
MAX_GAP_S = 2
MAX_SPEED_1080P_PX_PER_S = 130
MAX_EXTENSION_S = 20
STABLE_STEP_1080P_PX = 4
STABLE_STEPS = 3


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def extend(seed, rows):
    points = [{"time_s": p["time_s"],
               "center_1080p_px": p["center_1080p_px"],
               "cue": "body_template_plus_yellow_handle",
               "cue_score": p["score"]} for p in seed["points"]]
    last_seed_time = points[-1]["time_s"]
    decisions = []
    for row in rows:
        t = row["source_time_s"]
        if t <= last_seed_time:
            continue
        if t-last_seed_time > MAX_EXTENSION_S:
            break
        gap = t-points[-1]["time_s"]
        if gap > MAX_GAP_S:
            break
        available = []
        for candidate in row["positive_nms_points"]:
            distance = hypot(*(candidate["center_1080p_px"][axis] -
                               points[-1]["center_1080p_px"][axis]
                               for axis in (0, 1)))
            if distance <= MAX_SPEED_1080P_PX_PER_S*gap:
                available.append((distance, -candidate["score"], candidate))
        if not available:
            decisions.append({"time_s": t, "status": "no_cap_candidate_in_motion_gate"})
            continue
        distance, _, chosen = min(available)
        points.append({"time_s": t,
                       "center_1080p_px": chosen["center_1080p_px"],
                       "cue": "sideview_cap_context_positive",
                       "cue_score": chosen["score"]})
        decisions.append({"time_s": t, "status": "cap_candidate_linked",
                          "eligible_candidate_count": len(available),
                          "link_distance_1080p_px": round(distance, 2)})
        stop = split_moving_prefix(points, stable_step_px=STABLE_STEP_1080P_PX,
                                   stable_steps=STABLE_STEPS)
        if stop["visual_stop_bracket_s"] is not None:
            break
    stop = split_moving_prefix(points, stable_step_px=STABLE_STEP_1080P_PX,
                               stable_steps=STABLE_STEPS)
    return {"seed_path_id": seed["diagnostic_path_id"],
            "seed_interval_s": [seed["first_observed_s"], seed["last_observed_s"]],
            "points": points, "link_decisions": decisions,
            "image_motion_interpretation": stop,
            "physical_throw_verified": False,
            "same_stone_identity_verified": False,
            "physical_stop_verified": False,
            "ground_trajectory_verified": False,
            "simulation_ready": False}


def main():
    if OUT.exists():
        raise SystemExit("Output exists; preserve first handoff")
    body = json.loads(BODY.read_text())
    cap = json.loads(CAP.read_text())
    if body["target_video_sha256"] != cap["target_video_sha256"] or \
            body["source_interval_s"] != cap["source_interval_s"] or \
            body["sample_period_s"] != cap["sample_period_s"]:
        raise ValueError("Body and cap scans are not source aligned")
    seeds = [p for p in body["variants"]["frozen_score_0.45"]["image_motion_paths"]
             if p["direction"] == "upward"]
    joined = [extend(seed, cap["rows"]) for seed in seeds]
    result = {
        "status": "unpositioned_fullclip_template_to_cap_image_handoff_development",
        "target_video_sha256": body["target_video_sha256"],
        "body_ablation_sha256": digest(BODY),
        "cap_fullclip_sha256": digest(CAP),
        "stop_rule_code_sha256": digest(ROOT / "prototype/red_motion_window.py"),
        "runner_sha256": digest(Path(__file__)),
        "source_interval_s": body["source_interval_s"],
        "sample_period_s": 1,
        "max_link_gap_s": MAX_GAP_S,
        "max_link_speed_1080p_px_per_s": MAX_SPEED_1080P_PX_PER_S,
        "max_cap_extension_s": MAX_EXTENSION_S,
        "stable_step_1080p_px": STABLE_STEP_1080P_PX,
        "stable_consecutive_steps": STABLE_STEPS,
        "seed_path_count": len(seeds),
        "joined_image_paths": joined,
        "limitations": [
            "The body score 0.45 and wide-cap ROI were set after inspecting T11; this is not held-out transfer.",
            "Nearest-neighbour association can switch to a different stone or other yellow object.",
            "Visual stillness does not verify same-stone physical settling.",
            "No homography, physical stone identity, board state or spin is inferred.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"seed_paths": len(seeds),
                      "joined_paths": [{"seed": p["seed_interval_s"],
                                        "last": p["points"][-1]["time_s"],
                                        "stop_bracket": p["image_motion_interpretation"]["visual_stop_bracket_s"]}
                                       for p in joined]}))


if __name__ == "__main__":
    main()
