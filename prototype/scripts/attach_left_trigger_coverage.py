"""Combine a refined handoff with the frozen source-activity audit."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from left_trigger_coverage import attach_left_trigger_coverage


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("handoff", "activity", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    handoff, activity = [json.loads(path.read_text()) for path in (args.handoff, args.activity)]
    result = attach_left_trigger_coverage(handoff, activity)
    result["left_trigger_coverage_provenance"] = {
        "handoff_sha256": digest(args.handoff),
        "activity_audit_sha256": digest(args.activity),
        "model_code_sha256": digest(ROOT / "prototype/left_trigger_coverage.py"),
        "runner_sha256": digest(Path(__file__)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "rows": len(result["rows"]),
                "blind_seconds": result["left_trigger_blind_seconds"],
                "right_candidates_in_blind": result[
                    "right_view_candidate_ids_in_left_trigger_blind_interval"
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
