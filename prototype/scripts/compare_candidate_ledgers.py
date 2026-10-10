"""Write a provenance-checked comparison of two full-match candidate ledgers."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from ledger_comparison import compare_ledgers  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--augmented", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Comparison artifact already exists")
    baseline = json.loads(args.baseline.read_text())
    augmented = json.loads(args.augmented.read_text())
    for field in ("source_sha256", "source_interval_s"):
        if baseline[field] != augmented[field]:
            parser.error(f"Ledger {field} mismatch")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if baseline["source_sha256"] == reserved["source_sha256"]:
        parser.error("Reserved source cannot be used for development comparison")
    result = compare_ledgers(baseline["events"], augmented["events"])
    result.update({
        "status": "development_candidate_ledger_comparison_not_validation",
        "source_sha256": baseline["source_sha256"],
        "source_interval_s": baseline["source_interval_s"],
        "baseline_sha256": file_sha256(args.baseline),
        "augmented_sha256": file_sha256(args.augmented),
        "comparison_code_sha256": file_sha256(ROOT / "prototype/ledger_comparison.py"),
        "runner_sha256": file_sha256(__file__),
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print({"baseline": result["baseline_count"],
           "augmented": result["augmented_count"],
           "counter_changes": len(result["counter_changes"])})


if __name__ == "__main__":
    main()
