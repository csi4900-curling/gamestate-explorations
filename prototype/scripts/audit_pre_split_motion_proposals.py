"""Apply a fixed pre-split review rule to an artifact motion/patch/screen triple."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from pre_split_motion_proposal import (  # noqa: E402
    deduplicate_identical_prefixes, propose_pre_split_motion)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("motion", "patch", "screen", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    motion, patch, screen = (json.loads(getattr(args, name).read_text())
                             for name in ("motion", "patch", "screen"))
    source_id = motion.get("source_id", motion.get("candidate_source_id"))
    source_sha = motion.get("source_sha256", motion.get("candidate_source_sha256"))
    motion_sha = file_sha256(args.motion)
    patch_sha = file_sha256(args.patch)
    if patch["motion_sha256"] != motion_sha:
        parser.error("Artifact provenance differs")
    if source_id is not None:
        if (screen["source_id"] != source_id or
                screen["source_sha256"] != source_sha or
                screen["candidates_sha256"] != motion["candidates_sha256"]):
            parser.error("Source or candidate provenance differs")
    elif (screen.get("motion_sha256") != motion_sha or
          screen.get("patch_sha256") != patch_sha):
        parser.error("Screen does not chain to motion and patch artifacts")
    motion_rows = motion["rows"]
    by_patch = {row["candidate_id"]: row for row in patch["rows"]}
    by_decision = {row["candidate_id"]: row for row in screen["decisions"]}
    ids = [row["candidate_id"] for row in motion_rows]
    if (len(ids) != len(set(ids)) or set(ids) != set(by_patch) or
            not set(ids).issubset(by_decision)):
        parser.error("Candidate IDs differ across inputs")
    proposals = [proposal for row in motion_rows
                 if (proposal := propose_pre_split_motion(
                     row, by_patch[row["candidate_id"]],
                     by_decision[row["candidate_id"]])) is not None]
    unique = deduplicate_identical_prefixes(proposals)
    output = {
        "status": "postscore_pre_split_partial_review_proposals_not_event_validation",
        "source_id": source_id or screen["source_id"],
        "motion_sha256": file_sha256(args.motion),
        "patch_sha256": file_sha256(args.patch),
        "screen_sha256": file_sha256(args.screen),
        "rule_sha256": file_sha256(ROOT / "prototype/pre_split_motion_proposal.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "parameters": {"min_samples": 2, "min_travel_m": 1.0,
                       "min_scored_patches": 2, "min_positive_patches": 2},
        "candidate_count": len(ids),
        "screen_candidate_count": len(screen["decisions"]),
        "original_screen_status_counts": dict(Counter(row["status"] for row in
                                                    screen["decisions"])),
        "raw_proposal_count": len(proposals),
        "unique_proposal_count": len(unique),
        "proposals": unique,
        "limitations": [
            "The rule was selected after inspecting Canada-Czechia ambiguous paths; that match is development data.",
            "A short coloured-stone prefix does not prove delivery identity, event boundaries or post-contact identity.",
            "Identical-prefix deduplication does not catch all duplicate views or tracks.",
            "Conditional metric displacement and frozen patch scores are not independently calibrated throw labels.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(output["unique_proposal_count"], "unique proposals:",
          [(row["candidate_id"], row["duplicate_candidate_ids"])
           for row in unique])


if __name__ == "__main__":
    main()
