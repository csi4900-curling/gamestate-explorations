"""Postreview diagnostic of a strict two-view gate on exposed corridor data."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.throw_event_benchmark import evaluate_events


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("candidates", "corroboration", "reference", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    candidates = json.loads(args.candidates.read_text())
    corroboration = json.loads(args.corroboration.read_text())
    reference = json.loads(args.reference.read_text())
    if (corroboration["input_sha256"]["left"] != digest(args.candidates) or
            len({candidates["source_sha256"], corroboration["source_sha256"],
                 reference["source_sha256"]}) != 1 or
            candidates["source_interval_s"] != reference["source_interval_s"]):
        raise ValueError("Candidate, corroboration or reference provenance differs")
    by_id = {row["left_candidate_id"]: row for row in corroboration["rows"]}
    if (len(by_id) != len(corroboration["rows"]) or
            set(by_id) != {row["id"] for row in candidates["events"]}):
        raise ValueError("Candidate IDs differ")
    baseline = evaluate_events(candidates["events"], reference["events"],
                               reference["source_interval_s"])
    strict = [row for row in candidates["events"] if by_id[row["id"]][
        "corroboration_tier"] == "unique_right_time_colour_direction_candidate"]
    strict_score = evaluate_events(strict, reference["events"],
                                   reference["source_interval_s"])
    matched_ids = {row["prediction_id"] for row in baseline["matches"]}
    diagnostic_rows = [{
        "candidate_id": row["id"],
        "coarse_window_match_in_baseline": row["id"] in matched_ids,
        "corroboration_tier": by_id[row["id"]]["corroboration_tier"],
    } for row in candidates["events"]]
    output = {
        "status": "postreview_in_sample_diagnostic_not_detector_validation",
        "source_id": reference["source_id"],
        "source_sha256": reference["source_sha256"],
        "source_interval_s": reference["source_interval_s"],
        "reference_method": reference["reference_method"],
        "input_sha256": {"candidates": digest(args.candidates),
                         "corroboration": digest(args.corroboration),
                         "reference": digest(args.reference)},
        "scorer_code_sha256": digest(ROOT / "prototype/throw_event_benchmark.py"),
        "runner_sha256": digest(Path(__file__)),
        "baseline_score": baseline,
        "hypothetical_strict_two_view_score": strict_score,
        "baseline_matched_tiers": dict(Counter(
            row["corroboration_tier"] for row in diagnostic_rows
            if row["coarse_window_match_in_baseline"])),
        "baseline_extra_tiers": dict(Counter(
            row["corroboration_tier"] for row in diagnostic_rows
            if not row["coarse_window_match_in_baseline"])),
        "rows": diagnostic_rows,
        "limitations": [
            "Inputs and lag rule are from exposed recordings, not unseen validation.",
            "The same-agent coarse reference is not independently exhaustive.",
            "A right proposal matching time, colour and direction does not prove stone identity.",
            "This strict gate is hypothetical; it is not promoted to production filtering.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"source": reference["source_id"],
                      "baseline": [baseline[k] for k in
                                   ("true_positives", "false_positives", "false_negatives")],
                      "strict": [strict_score[k] for k in
                                 ("true_positives", "false_positives", "false_negatives")]}))


if __name__ == "__main__":
    main()
