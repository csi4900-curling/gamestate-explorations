"""Exclude exact duplicate triggers only from a partial-board tail clock."""

import argparse
from collections import Counter
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
    parser.add_argument("--target-candidate", required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Deduplicated tail input directory already exists")
    proposals, candidates, motion, screen = (
        json.loads(getattr(args, key).read_text()) for key in
        ("proposals", "candidates", "motion", "screen"))
    if (screen["candidates_sha256"] != file_sha256(args.candidates) or
            screen["motion_sha256"] != file_sha256(args.motion) or
            screen["proposals_sha256"] != file_sha256(args.proposals)):
        parser.error("Target input provenance differs")
    proposal = next((row for row in proposals["proposals"]
                     if row["candidate_id"] == args.target_candidate), None)
    if not proposal or not proposal["duplicate_candidate_ids"]:
        parser.error("Target has no exact-prefix duplicate")
    duplicate_ids = set(proposal["duplicate_candidate_ids"])
    by_motion = {row["candidate_id"]: row for row in motion["rows"]}
    by_candidate = {row["id"]: row for row in candidates["events"]}
    if not duplicate_ids.issubset(by_motion) or not duplicate_ids.issubset(by_candidate):
        parser.error("Duplicate target is missing")
    for pid in duplicate_ids:
        other = by_motion[pid]
        if (other["selection"]["status"] != "ambiguous_far_entry_motion_paths" or
                other["selection"]["shared_prefix"] != proposal["prefix_samples"] or
                other["colour"] != proposal["colour"] or
                other["receiving_view"] != proposal["receiving_view"]):
            parser.error(f"Duplicate motion differs: {pid}")
    if [row["id"] for row in screen["events"] if row["id"] ==
            args.target_candidate] != [args.target_candidate]:
        parser.error("Target does not occur exactly once")
    filtered_candidates = {**candidates,
                           "status": "tail_clock_excludes_exact_prefix_duplicate_only",
                           "parent_candidates_sha256": file_sha256(args.candidates),
                           "events": [row for row in candidates["events"]
                                      if row["id"] not in duplicate_ids]}
    if "candidate_count" in filtered_candidates:
        filtered_candidates["candidate_count"] = len(filtered_candidates["events"])
    filtered_motion = {**motion,
                       "status": "tail_clock_excludes_exact_prefix_duplicate_only",
                       "parent_target_motion_sha256": file_sha256(args.motion),
                       "rows": [row for row in motion["rows"]
                                if row["candidate_id"] not in duplicate_ids]}
    if "candidate_count" in filtered_motion:
        filtered_motion["candidate_count"] = len(filtered_motion["rows"])
    if "selection_status_counts" in filtered_motion:
        filtered_motion["selection_status_counts"] = dict(Counter(
            row["selection"]["status"] for row in filtered_motion["rows"]))
    args.output_dir.mkdir(parents=True)
    candidate_path = args.output_dir / "candidates.json"
    motion_path = args.output_dir / "motion.json"
    candidate_path.write_text(json.dumps(filtered_candidates, indent=2) + "\n")
    filtered_motion["candidates_sha256"] = file_sha256(candidate_path)
    motion_path.write_text(json.dumps(filtered_motion, indent=2) + "\n")
    filtered_screen = {**screen,
                       "status": "single_partial_board_target_with_duplicate_omitted_from_tail_clock",
                       "events": [row for row in screen["events"]
                                  if row["id"] == args.target_candidate],
                       "parent_target_screen_sha256": file_sha256(args.screen),
                       "candidates_sha256": file_sha256(candidate_path),
                       "motion_sha256": file_sha256(motion_path)}
    screen_path = args.output_dir / "screen.json"
    screen_path.write_text(json.dumps(filtered_screen, indent=2) + "\n")
    (args.output_dir / "manifest.json").write_text(json.dumps({
        "status": "tail_clock_deduplication_not_event_screen_change",
        "target_candidate_id": args.target_candidate,
        "excluded_exact_duplicate_ids": sorted(duplicate_ids),
        "original_candidate_count": len(candidates["events"]),
        "tail_clock_candidate_count": len(filtered_candidates["events"]),
        "input_sha256": {key: file_sha256(getattr(args, key)) for key in
                         ("proposals", "candidates", "motion", "screen")},
        "output_sha256": {"candidates": file_sha256(candidate_path),
                          "motion": file_sha256(motion_path),
                          "screen": file_sha256(screen_path)},
        "runner_sha256": file_sha256(Path(__file__)),
    }, indent=2) + "\n")
    print(args.target_candidate, "tail clock excludes", sorted(duplicate_ids))


if __name__ == "__main__":
    main()
