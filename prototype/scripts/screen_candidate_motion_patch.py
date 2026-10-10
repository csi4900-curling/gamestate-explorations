"""Build a reference-free two-cue screen for frozen passage candidates."""

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
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Screen artifact already exists")
    candidates = json.loads(args.candidates.read_text())
    motion = json.loads(args.motion.read_text())
    patch = json.loads(args.patch.read_text())
    if motion["candidates_sha256"] != file_sha256(args.candidates) or (
        patch["motion_sha256"] != file_sha256(args.motion)
    ):
        parser.error("Candidate, motion, and patch artifacts do not chain")
    by_motion = {row["candidate_id"]: row for row in motion["rows"]}
    by_patch = {row["candidate_id"]: row for row in patch["rows"]}
    ids = [row["id"] for row in candidates["events"]]
    if len(set(ids)) != len(ids) or set(ids) != set(by_motion) or set(ids) != set(by_patch):
        parser.error("Candidate IDs differ across inputs")
    decisions = [screen_candidate(by_motion[pid], by_patch[pid]) for pid in ids]
    accepted_ids = {decision["candidate_id"] for decision in decisions if decision["accepted"]}
    result = {
        "status": "development_candidate_motion_patch_screen_not_independent_validation",
        "source_id": candidates["source_id"],
        "source_sha256": candidates["source_sha256"],
        "source_interval_s": candidates["source_interval_s"],
        "candidates_sha256": file_sha256(args.candidates),
        "motion_sha256": file_sha256(args.motion),
        "patch_sha256": file_sha256(args.patch),
        "screen_code_sha256": file_sha256(ROOT / "prototype/candidate_motion_patch_screen.py"),
        "runner_sha256": file_sha256(__file__),
        "decisions": decisions,
        "decision_status_counts": dict(Counter(row["status"] for row in decisions)),
        "events": [row for row in candidates["events"] if row["id"] in accepted_ids],
        "limitations": [
            "This rule was assembled after inspecting this match's false D11 path and is in-sample development.",
            "The stone-patch model is frozen but trained on small agent-labelled crops from other exposed matches.",
            "One positive patch among three sampled path points is not proof of persistent stone identity.",
            "An abstention or negative patch check does not prove there was no throw.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["decision_status_counts"], "accepted", len(result["events"]))


if __name__ == "__main__":
    main()
