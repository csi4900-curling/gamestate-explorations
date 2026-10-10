"""Freeze the highest comovement accepted candidates for source inspection."""

import argparse
from hashlib import sha256
import json
from pathlib import Path


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--triage", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument(
        "--isolated-withheld",
        action="store_true",
        help="Select all previously withheld isolated-motion cues",
    )
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first selection")
    if args.count <= 0:
        parser.error("Count must be positive")
    triage = json.loads(args.triage.read_text())
    if args.isolated_withheld:
        selected = sorted(
            (
                row
                for row in triage["rows"]
                if not row["previously_auto_accepted"]
                and row["context_cue"] == "isolated_motion_cue"
            ),
            key=lambda row: (row["candidate_time_s"], row["candidate_id"]),
        )
        if not selected:
            parser.error("No isolated-motion withheld candidates")
        rule = "all previously withheld isolated-motion cues in time order"
    else:
        candidates = [
            row
            for row in triage["rows"]
            if row["previously_auto_accepted"] and row["comovement_index"] is not None
        ]
        candidates.sort(
            key=lambda row: (-row["comovement_index"], row["candidate_time_s"], row["candidate_id"])
        )
        if len(candidates) < args.count:
            parser.error("Fewer scored accepted candidates than requested")
        selected = candidates[: args.count]
        rule = "highest full-ring comovement index among previously accepted candidates; earlier time then ID breaks ties"
    result = {
        "status": "prediction_ranked_source_review_selection_not_event_truth",
        "source_sha256": triage["source_sha256"],
        "triage_sha256": digest(args.triage),
        "selection_rule": rule,
        "count": len(selected),
        "selected": selected,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"ids": [row["candidate_id"] for row in selected]}))


if __name__ == "__main__":
    main()
