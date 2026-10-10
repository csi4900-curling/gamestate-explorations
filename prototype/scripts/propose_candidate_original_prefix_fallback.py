"""Audit original motion prefixes lost by the broad dropout retry."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from candidate_prefix_fallback import propose_original_prefix  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("base", "retry", "patch", "screen", "output"):
        parser.add_argument(f"--{key}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Prefix fallback artifact already exists")
    base, retry, patch, screen = (json.loads(getattr(args, key).read_text())
                                  for key in ("base", "retry", "patch", "screen"))
    if (retry["source_motion_sha256"] != file_sha256(args.base) or
            patch["motion_sha256"] != file_sha256(args.base) or
            screen["motion_sha256"] != file_sha256(args.retry) or
            patch["video_sha256"] != retry["high_resolution_source_sha256"]):
        parser.error("Base, retry, patch, or screen provenance differs")
    by_retry = {row["candidate_id"]: row for row in retry["rows"]}
    by_patch = {row["candidate_id"]: row for row in patch["rows"]}
    by_decision = {row["candidate_id"]: row for row in screen["decisions"]}
    ids = [row["candidate_id"] for row in base["rows"]]
    if (len(ids) != len(set(ids)) or set(ids) != set(by_retry) or
            set(ids) != set(by_patch) or set(ids) != set(by_decision) or
            any(len(rows) != len(ids) for rows in (by_retry, by_patch,
                                                   by_decision))):
        parser.error("Candidate evidence IDs differ")
    proposals = []
    for row in base["rows"]:
        pid = row["candidate_id"]
        if by_decision[pid]["accepted"]:
            continue
        proposal = propose_original_prefix(row, by_retry[pid], by_patch[pid])
        if proposal:
            proposals.append(proposal)
    output = {
        "status": "postscore_exposed_development_prefix_proposals_not_event_validation",
        "base_sha256": file_sha256(args.base),
        "retry_sha256": file_sha256(args.retry),
        "patch_sha256": file_sha256(args.patch),
        "screen_sha256": file_sha256(args.screen),
        "model_code_sha256": file_sha256(ROOT / "prototype" /
                                         "candidate_prefix_fallback.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "parameters": {"min_samples": 5, "min_fraction": 0.7,
                       "min_travel_m": 2.0, "min_scored_patches": 3,
                       "min_positive_patches": 2},
        "proposal_count": len(proposals),
        "proposals": proposals,
        "limitations": [
            "This rule was formed after inspecting the exposed Slovakia S02 failure.",
            "Appearance and shared motion support a proposal, not a verified throw or release time.",
            "No position or identity is asserted beyond the original shared prefix.",
            "The frozen screen and its previous transfer results are unchanged.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print([(row["candidate_id"], row["prefix_sample_count"],
            row["positive_patch_count"]) for row in proposals])


if __name__ == "__main__":
    main()
