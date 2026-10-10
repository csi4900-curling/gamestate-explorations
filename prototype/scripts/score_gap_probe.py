"""Score raw and screened gap candidates against frozen coarse windows.

This is a development diagnostic, not complete-recording throw-event F1.
"""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from throw_event_benchmark import evaluate_events


def totals(rows):
    tp = sum(row["true_positives"] for row in rows)
    fp = sum(row["false_positives"] for row in rows)
    fn = sum(row["false_negatives"] for row in rows)
    ctp = sum(row["colour_aware_true_positives"] for row in rows)
    cfp = sum(row["colour_aware_false_positives"] for row in rows)
    cfn = sum(row["colour_aware_false_negatives"] for row in rows)
    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
        "colour_aware_true_positives": ctp,
        "colour_aware_false_positives": cfp,
        "colour_aware_false_negatives": cfn,
        "colour_aware_f1": 2 * ctp / (2 * ctp + cfp + cfn)
        if 2 * ctp + cfp + cfn
        else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--screen", type=Path, required=True)
    parser.add_argument("--reference", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve the earlier score")
    raw = json.loads(args.raw.read_text())
    screen = json.loads(args.screen.read_text())
    if (
        raw["source_id"] != screen["source_id"]
        or raw["source_sha256"] != screen["source_sha256"]
        or screen["input_sha256"] != file_sha256(args.raw)
    ):
        parser.error("Raw and screened artifacts disagree")
    stages = {
        "raw": raw["motion_candidates"],
        "screen": screen["corroborated_candidates"],
    }
    references = [json.loads(path.read_text()) for path in args.reference]
    per_gap = []
    for path, reference in zip(args.reference, references):
        if (
            reference["source_id"] != raw["source_id"]
            or reference["source_sha256"] != raw["source_sha256"]
        ):
            parser.error(f"Reference source differs: {path}")
        lo, hi = reference["source_interval_s"]
        containing_gaps = [
            gap["id"]
            for gap in raw["scanned_gaps"]
            if gap["interval_s"][0] <= lo < hi <= gap["interval_s"][1]
        ]
        if len(containing_gaps) != 1:
            parser.error(f"Reference must lie within exactly one scanned gap: {path}")
        gap_id = containing_gaps[0]
        row = {
            "gap_id": gap_id,
            "reference_path": str(path),
            "reference_sha256": file_sha256(path),
            "scored_interval_s": [lo, hi],
        }
        for name, candidates in stages.items():
            selected = [
                item
                for item in candidates
                if item["gap_id"] == gap_id and lo <= item["crossing_time_s"] <= hi
            ]
            row[name] = evaluate_events(selected, reference["events"], [lo, hi])
        per_gap.append(row)
    result = {
        "status": "development_gap_candidate_score",
        "source_id": raw["source_id"],
        "source_sha256": raw["source_sha256"],
        "raw_sha256": file_sha256(args.raw),
        "screen_sha256": file_sha256(args.screen),
        "scorer_sha256": file_sha256(ROOT / "prototype/throw_event_benchmark.py"),
        "runner_sha256": file_sha256(__file__),
        "per_gap": per_gap,
        "totals": {name: totals([row[name] for row in per_gap]) for name in stages},
        "limitations": [
            "References are coarse agent-authored development windows, not independent validation.",
            "Only declared interior gap subintervals are scored; boundary portions are excluded.",
            "Candidate F1 is not confirmed throw-event F1 or a complete-recording score.",
        ],
    }
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result["totals"], indent=2))


if __name__ == "__main__":
    main()
