"""Audit strong shared motion prefixes withheld by the unique-path screen."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from candidate_shared_prefix_proposal import propose_shared_prefix  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("motion", "patch", "screen", "output"):
        parser.add_argument(f"--{key}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Prefix proposal output already exists")
    motion, patch, screen = (json.loads(getattr(args, key).read_text())
                             for key in ("motion", "patch", "screen"))
    if patch["motion_sha256"] != file_sha256(args.motion) or \
            screen["motion_sha256"] != file_sha256(args.motion) or \
            screen["patch_sha256"] != file_sha256(args.patch):
        parser.error("Motion, patch, and screen artifacts do not chain")
    by_patch = {row["candidate_id"]: row for row in patch["rows"]}
    by_decision = {row["candidate_id"]: row for row in screen["decisions"]}
    ids = [row["candidate_id"] for row in motion["rows"]]
    if (len(ids) != len(set(ids)) or set(ids) != set(by_patch) or
            set(ids) != set(by_decision)):
        parser.error("Candidate IDs differ")
    proposals = []
    for row in motion["rows"]:
        pid = row["candidate_id"]
        if by_decision[pid]["accepted"]:
            continue
        proposal = propose_shared_prefix(row, by_patch[pid])
        if proposal is not None:
            proposals.append(proposal)
    output = {
        "status": "postscore_development_partial_prefix_review_not_event_validation",
        "source_id": screen["source_id"],
        "motion_sha256": file_sha256(args.motion),
        "patch_sha256": file_sha256(args.patch),
        "screen_sha256": file_sha256(args.screen),
        "model_code_sha256": file_sha256(
            ROOT / "prototype/candidate_shared_prefix_proposal.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "parameters": {"min_samples": 5, "min_fraction": 0.7,
                       "min_travel_m": 2.0, "min_scored_patches": 3,
                       "min_positive_patches": 2},
        "proposal_count": len(proposals),
        "proposals": proposals,
        "limitations": [
            "This rule was applied after seeing the Latvia S21 abstention and cannot change its frozen first-transfer result.",
            "The shared prefix is visible motion evidence, not verified delivery identity or a complete trajectory.",
            "Conditional displacement inherits unvalidated camera geometry.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print([(r["candidate_id"], r["prefix_sample_count"],
            r["positive_patch_count"]) for r in proposals])


if __name__ == "__main__":
    main()
