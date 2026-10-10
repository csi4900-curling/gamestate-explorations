"""Attach 2024 displayed-end observations to the full-match evidence union."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from full_match_display_join import attach_display_context


def digest(path):
    result = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--union", type=Path, required=True)
    parser.add_argument("--display", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    union = json.loads(args.union.read_text())
    display = json.loads(args.display.read_text())
    joined = attach_display_context(union, display)
    output = {
        "status": "provisional_full_match_evidence_with_displayed_end_context_not_physical_end_state",
        "source_id": union["source_id"],
        "source_sha256": union["source_sha256"],
        "source_interval_s": union["source_interval_s"],
        "union_sha256": digest(args.union),
        "display_sha256": digest(args.display),
        "join_code_sha256": digest(ROOT / "prototype/full_match_display_join.py"),
        "runner_sha256": digest(Path(__file__)),
        **joined,
        "limitations": [
            "The displayed end can lag physical play and cannot assign physical end identity.",
            "Unknown and changing graphic contexts remain unknown; no end is interpolated across them.",
            "Screen and pre-split rows remain provisional or review-only, not verified throws.",
            "Partial boards remain incomplete and uncalibrated; no row is simulation-ready.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {
                "raw": joined["raw_trigger_count"],
                "context_statuses": joined["context_status_counts"],
                "ends": joined["bracketed_candidate_tiers_by_displayed_end"],
            }
        )
    )


if __name__ == "__main__":
    main()
