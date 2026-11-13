"""Write non-destructive colour and delayed-counter ambiguity audit."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from prototype.event_identity_audit import audit_event_identity


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--learned-motion", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first identity audit")
    ledger = json.loads(args.ledger.read_text())
    learned = json.loads(args.learned_motion.read_text())
    if (
        ledger["source_sha256"] != learned["source_sha256"]
        or ledger["source_interval_s"] != learned["source_interval_s"]
    ):
        parser.error("Evidence source or interval fingerprints differ")
    rows = audit_event_identity(ledger["events"], learned["shots"])
    result = {
        "status": "development_identity_ambiguity_audit_not_event_predictions",
        "source_sha256": ledger["source_sha256"],
        "source_interval_s": ledger["source_interval_s"],
        "ledger_sha256": digest(args.ledger),
        "learned_motion_sha256": digest(args.learned_motion),
        "audit_code_sha256": digest(
            Path(__file__).resolve().parents[1] / "event_identity_audit.py"
        ),
        "runner_sha256": digest(Path(__file__)),
        "candidate_count": len(rows),
        "visual_only_colour_collision_risk_count": sum(
            row["visual_only_colour_collision_risk"] for row in rows
        ),
        "alternative_colour_hypothesis_count": sum(
            row["earliest_following_colour_hypothesis"] is not None
            and row["earliest_following_colour_hypothesis"] != row["ledger_colour"]
            for row in rows
        ),
        "possible_delayed_counter_relation_count": sum(
            len(row["possible_delayed_counter_links"]) for row in rows
        ),
        "rows": rows,
        "limitations": [
            "Risk flags and possible links are not confirmed same-stone identities or throw decisions.",
            "Unscanned learned-motion shots cannot supply negative colour evidence.",
            "Moving stones in the house may be collision effects, not the delivered stone.",
            "The earliest-following-motion colour rule was developed after inspecting Slovakia source examples; it requires a new frozen transfer check.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "candidate_count",
                    "visual_only_colour_collision_risk_count",
                    "possible_delayed_counter_relation_count",
                    "alternative_colour_hypothesis_count",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
