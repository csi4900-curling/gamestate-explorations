"""Screen label-free dropout rescues using stone patches and shared-path dedup."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from candidate_motion_rescue_screen import screen_rescue_candidate  # noqa: E402
from motion_path_dedup import deduplicate_motion_paths  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--motion", type=Path, required=True)
    parser.add_argument("--patch", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Rescue screen already exists")
    candidates = json.loads(args.candidates.read_text())
    motion = json.loads(args.motion.read_text())
    patch = json.loads(args.patch.read_text())
    if patch["motion_sha256"] != file_sha256(args.motion):
        parser.error("Patch and motion artifacts do not chain")
    ids = [event["id"] for event in candidates["events"]]
    motions = {row["candidate_id"]: row for row in motion["rows"]}
    patches = {row["candidate_id"]: row for row in patch["rows"]}
    if len(set(ids)) != len(ids) or any(set(rows) != set(ids)
                                    for rows in (motions, patches)):
        parser.error("Candidate IDs differ")
    decisions = [screen_rescue_candidate(motions[pid], patches[pid]) for pid in ids]
    by_decision = {row["candidate_id"]: row for row in decisions}
    eligible_rows = []
    for pid in ids:
        row = dict(motions[pid])
        if not by_decision[pid]["accepted"]:
            row["selection"] = {"path": []}
        eligible_rows.append(row)
    dedup = deduplicate_motion_paths(candidates["events"], eligible_rows)
    for row in dedup["decisions"]:
        pid = row["candidate_id"]
        if by_decision[pid]["accepted"] and row["status"] != "primary_motion_path":
            by_decision[pid].update(
                status="duplicate_shared_timed_motion_path", accepted=False,
                primary_candidate_id=row["primary_candidate_id"])
    retained = {row["candidate_id"] for row in decisions if row["accepted"]}
    result = {
        "status": "postscore_exposed_development_dropout_rescue_screen_not_transfer_validation",
        "source_id": candidates["source_id"],
        "source_sha256": candidates["source_sha256"],
        "source_interval_s": candidates["source_interval_s"],
        "candidates_sha256": file_sha256(args.candidates),
        "motion_sha256": file_sha256(args.motion),
        "patch_sha256": file_sha256(args.patch),
        "screen_code_sha256": file_sha256(
            ROOT / "prototype/candidate_motion_rescue_screen.py"),
        "dedup_code_sha256": file_sha256(ROOT / "prototype/motion_path_dedup.py"),
        "runner_sha256": file_sha256(__file__),
        "shared_timed_path_pairs": dedup["pairs"],
        "decisions": decisions,
        "decision_status_counts": dict(Counter(row["status"] for row in decisions)),
        "events": [event for event in candidates["events"]
                   if event["id"] in retained],
        "limitations": [
            "The rescue rule was designed after seeing exposed Italy, Estonia and China errors.",
            "Shared prefixes prove neither later path identity nor complete throw trajectories.",
            "Accepted patch scores are visual cues, not independently validated physical stone identity.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["decision_status_counts"], "accepted", len(result["events"]))


if __name__ == "__main__":
    main()
