"""Audit same-colour adjacent observations in a routed event timeline."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from event_sequence_consistency import audit_sequence


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeline", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first sequence audit")
    timeline = json.loads(args.timeline.read_text())
    if "observed_events" not in timeline or "coverage_gaps_s" not in timeline:
        parser.error("Input must be a gap-aware routed timeline")
    rows = audit_sequence(timeline["observed_events"], timeline["coverage_gaps_s"])
    result = {
        "status": "development_sequence_consistency_audit_not_throw_truth",
        "source_id": timeline["source_id"],
        "source_sha256": timeline["source_sha256"],
        "source_interval_s": timeline["source_interval_s"],
        "timeline_sha256": digest(args.timeline),
        "audit_code_sha256": digest(ROOT / "prototype/event_sequence_consistency.py"),
        "runner_sha256": digest(Path(__file__)),
        "same_colour_adjacent_count": len(rows),
        "nearby_review_priority_count": sum(row["nearby_review_priority"] for row in rows),
        "rows": rows,
        "limitations": [
            "Teams alternate within an end, but end boundaries and rare redeliveries are not verified here.",
            "A same-colour pair can represent an extra event, missed opponent throw, colour error or new end.",
            "This audit never inserts, removes or recolours event predictions.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {"same_colour": len(rows), "nearby_priority": result["nearby_review_priority_count"]}
        )
    )


if __name__ == "__main__":
    main()
