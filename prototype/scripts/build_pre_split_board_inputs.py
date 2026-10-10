"""Prepare quiet-tail board observation targets from pre-split proposals."""

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("proposals", "candidates", "motion", "screen", "output_dir"):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Board input directory already exists")
    proposals, candidates, motion, screen = (
        json.loads(getattr(args, key).read_text())
        for key in ("proposals", "candidates", "motion", "screen")
    )
    if (
        proposals["screen_sha256"] != file_sha256(args.screen)
        or screen["candidates_sha256"] != file_sha256(args.candidates)
        or proposals["source_id"] != candidates["source_id"]
        or screen["source_sha256"] != candidates["source_sha256"]
        or motion["candidates_sha256"] != file_sha256(args.candidates)
    ):
        parser.error("Input provenance differs")
    by_candidate = {row["id"]: row for row in candidates["events"]}
    by_decision = {row["candidate_id"]: row for row in screen["decisions"]}
    by_motion = {row["candidate_id"]: row for row in motion["rows"]}
    if len(by_candidate) != len(candidates["events"]) or len(by_motion) != len(motion["rows"]):
        parser.error("Duplicate input candidate ID")
    ids = [row["candidate_id"] for row in proposals["proposals"]]
    if len(ids) != len(set(ids)) or not set(ids).issubset(by_candidate):
        parser.error("Invalid review proposal IDs")
    target_motion = deepcopy(motion)
    target_by = {row["candidate_id"]: row for row in target_motion["rows"]}
    for proposal in proposals["proposals"]:
        pid = proposal["candidate_id"]
        candidate = by_candidate[pid]
        original = by_motion[pid]
        target = target_by[pid]
        if (
            by_decision[pid]["accepted"]
            or original["selection"]["status"] != "ambiguous_far_entry_motion_paths"
            or original["selection"]["shared_prefix"] != proposal["prefix_samples"]
            or candidate["colour"] != proposal["colour"]
            or candidate["crossing_time_s"] != proposal["crossing_time_s"]
            or original["receiving_view"] != proposal["receiving_view"]
        ):
            parser.error(f"Pre-split target differs: {pid}")
        target["base_selection"] = target["selection"]
        target["selection"] = {
            "status": "pre_split_partial_board_observation_target_not_event_acceptance",
            "path": proposal["prefix_samples"],
            "first_ambiguity_time_s": proposal["first_ambiguity_time_s"],
            "physical_identity_verified": False,
            "simulation_ready": False,
        }
    target_motion["status"] = "board_observation_adapter_not_accepted_throw_motion"
    target_motion["parent_motion_sha256"] = file_sha256(args.motion)
    target_motion["proposals_sha256"] = file_sha256(args.proposals)
    args.output_dir.mkdir(parents=True)
    motion_path = args.output_dir / "motion.json"
    motion_path.write_text(json.dumps(target_motion, indent=2) + "\n")
    target_screen = {
        "status": "quiet_tail_board_targets_not_event_acceptances",
        "source_id": candidates["source_id"],
        "source_sha256": candidates["source_sha256"],
        "source_interval_s": candidates["source_interval_s"],
        "candidates_sha256": file_sha256(args.candidates),
        "motion_sha256": file_sha256(motion_path),
        "parent_screen_sha256": file_sha256(args.screen),
        "proposals_sha256": file_sha256(args.proposals),
        "events": [by_candidate[pid] for pid in ids],
    }
    screen_path = args.output_dir / "screen.json"
    screen_path.write_text(json.dumps(target_screen, indent=2) + "\n")
    manifest = {
        "status": "pre_split_board_observation_targets_not_accepted_throws",
        "input_sha256": {
            key: file_sha256(getattr(args, key))
            for key in ("proposals", "candidates", "motion", "screen")
        },
        "runner_sha256": file_sha256(Path(__file__)),
        "target_motion_sha256": file_sha256(motion_path),
        "target_screen_sha256": file_sha256(screen_path),
        "target_candidate_ids": ids,
        "candidate_denominator": len(candidates["events"]),
        "next_passage_bound_source": "all corridor candidates, not only board targets",
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(len(ids), "quiet-tail targets from", len(candidates["events"]), "corridor candidates")


if __name__ == "__main__":
    main()
