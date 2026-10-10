"""Derive tentative moving prefixes from the full 1080p red image paths."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from red_motion_window import split_moving_prefix

BASE = ROOT / "validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1"
TRANSFER = BASE / "early-highres-red-full-transfer-development.json"
OUT = BASE / "early-highres-red-motion-windows-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise SystemExit("Output exists; preserve first motion interpretation")
    transfer = json.loads(TRANSFER.read_text())
    derived = []
    for path in transfer["supported_image_paths"]:
        if path["direction"] != "upward":
            continue
        derived.append({
            "diagnostic_path_id": path["diagnostic_path_id"],
            "raw_image_path_interval_s": [path["first_observed_s"],
                                          path["last_observed_s"]],
            "raw_path_observation_count": len(path["points"]),
            **split_moving_prefix(path["points"]),
            "physical_release_verified": False,
            "physical_stop_verified": False,
            "same_stone_identity_through_stop_verified": False,
            "simulation_ready": False,
        })
    by_id = {r["diagnostic_path_id"]: r for r in derived}
    context = []
    for candidate in transfer["candidate_context"]:
        context.append({
            "candidate_id": candidate["candidate_id"],
            "crossing_time_s": candidate["crossing_time_s"],
            "associated_motion_windows": [by_id[x] for x in candidate[
                "upward_path_ids_started_within_25s"]],
            "physical_throw_verified": False,
        })
    result = {
        "status": "visual_motion_prefixes_not_physical_throw_or_settle_times",
        "transfer_sha256": digest(TRANSFER),
        "rule_code_sha256": digest(ROOT / "prototype/red_motion_window.py"),
        "runner_sha256": digest(Path(__file__)),
        "stable_step_max_1080p_px_per_s": 4,
        "stable_consecutive_one_second_steps": 3,
        "paths": derived,
        "candidate_context": context,
        "limitations": [
            "The first stillness run can be a parked-stone identity switch, not the delivered stone stopping.",
            "Camera cuts or occlusion can right-censor motion before the stone settles.",
            "One-second sampling brackets image stillness; it cannot time the physical stop exactly.",
            "No physical post-throw board is inferred from these image paths.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"visual_stop_candidates": sum(
        r["visual_stop_bracket_s"] is not None for r in derived),
        "right_censored": sum(r["visual_stop_bracket_s"] is None
                              for r in derived),
        "paths": len(derived)}))


if __name__ == "__main__":
    main()
