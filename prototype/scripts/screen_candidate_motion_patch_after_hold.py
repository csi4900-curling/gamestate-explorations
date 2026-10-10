"""Postscore two-cue screen after explicit registration hold and path dedup."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from candidate_motion_patch_screen import screen_candidate  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--motion", type=Path, required=True)
    parser.add_argument("--patch", type=Path, required=True)
    parser.add_argument("--dedup", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Postscore screen already exists")
    candidates = json.loads(args.candidates.read_text())
    motion = json.loads(args.motion.read_text())
    patch = json.loads(args.patch.read_text())
    dedup = json.loads(args.dedup.read_text())
    if (
        patch["motion_sha256"] != file_sha256(args.motion)
        or (dedup["motion_sha256"] != file_sha256(args.motion))
        or (dedup["candidates_sha256"] != file_sha256(args.candidates))
    ):
        parser.error("Input artifact chain differs")
    motions = {row["candidate_id"]: row for row in motion["rows"]}
    patches = {row["candidate_id"]: row for row in patch["rows"]}
    deduped = {row["candidate_id"]: row for row in dedup["decisions"]}
    ids = [event["id"] for event in candidates["events"]]
    if len(set(ids)) != len(ids) or any(
        set(rows) != set(ids) for rows in (motions, patches, deduped)
    ):
        parser.error("Candidate IDs differ")
    decisions = []
    for pid in ids:
        decision = screen_candidate(motions[pid], patches[pid])
        if decision["accepted"] and deduped[pid]["status"] != "primary_motion_path":
            decision["accepted"] = False
            decision["status"] = "duplicate_shared_timed_motion_path"
            decision["primary_candidate_id"] = deduped[pid]["primary_candidate_id"]
        decisions.append(decision)
    accepted = {row["candidate_id"] for row in decisions if row["accepted"]}
    result = {
        "status": "postscore_in_sample_registration_hold_gap_and_dedup_screen",
        "source_id": candidates["source_id"],
        "source_sha256": candidates["source_sha256"],
        "source_interval_s": candidates["source_interval_s"],
        "candidates_sha256": file_sha256(args.candidates),
        "motion_sha256": file_sha256(args.motion),
        "patch_sha256": file_sha256(args.patch),
        "dedup_sha256": file_sha256(args.dedup),
        "runner_sha256": file_sha256(__file__),
        "decisions": decisions,
        "decision_status_counts": dict(Counter(row["status"] for row in decisions)),
        "events": [event for event in candidates["events"] if event["id"] in accepted],
        "limitations": [
            "Registration hold, bounded gaps, and duplicate-path suppression were designed after the frozen Estonia transfer failed.",
            "The same developer has inspected this source and reference; this result is not independent validation.",
            "Borrowed camera transforms and unobserved gaps do not establish physical stone identity or metric accuracy.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["decision_status_counts"], "accepted", len(result["events"]))


if __name__ == "__main__":
    main()
