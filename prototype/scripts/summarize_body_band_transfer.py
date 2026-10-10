"""Aggregate the unchanged 0.5 body-band rule across pre-existing 2024 screens."""

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", nargs="+", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Summary already exists")
    rows = []
    for path in args.inputs:
        result = json.loads(path.read_text())
        if result["neutral_gray_fraction_threshold"] != 0.5:
            parser.error(f"Threshold differs: {path}")
        accepted = [row for row in result["decisions"] if row["accepted"]]
        if len(accepted) != result["development_accepted_count"] or (
                result["frozen_accepted_count"] - len(accepted) !=
                len(result["flagged_candidate_ids"])):
            parser.error(f"Decision counts differ: {path}")
        fractions = [row["max_neutral_gray_fraction"] for row in result["decisions"]
                     if row.get("max_neutral_gray_fraction") is not None]
        rows.append({
            "source_id": result["source_id"],
            "source_sha256": result["source_sha256"],
            "input_file": str(path),
            "input_sha256": file_sha256(path),
            "frozen_accepted_count": result["frozen_accepted_count"],
            "development_accepted_count": result["development_accepted_count"],
            "flagged_candidate_ids": result["flagged_candidate_ids"],
            "minimum_measured_candidate_fraction": min(fractions) if fractions else None,
        })
    if len({row["source_sha256"] for row in rows}) != len(rows):
        parser.error("Input recordings are not distinct")
    output = {
        "status": "postscore_development_body_band_transfer_summary_not_independent_accuracy",
        "runner_sha256": file_sha256(Path(__file__)),
        "threshold": 0.5,
        "recording_count": len(rows),
        "frozen_accepted_total": sum(row["frozen_accepted_count"] for row in rows),
        "development_accepted_total": sum(row["development_accepted_count"] for row in rows),
        "flagged_total": sum(len(row["flagged_candidate_ids"]) for row in rows),
        "rows": rows,
        "limitations": [
            "This compares decisions on six exposed 2024 recording segments, not independent throw ground truth.",
            "A flagged candidate is an abstention; remaining acceptances are still provisional.",
            "The feature and threshold were chosen after inspecting Canada-Czechia false positives.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(output["recording_count"], "recordings;",
          output["frozen_accepted_total"], "->",
          output["development_accepted_total"], "accepted")


if __name__ == "__main__":
    main()
