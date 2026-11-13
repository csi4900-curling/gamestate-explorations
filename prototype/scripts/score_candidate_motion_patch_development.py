"""Score the exposed Canada–China two-cue screen against coarse development windows."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from throw_event_benchmark import evaluate_events  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screen", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Development score already exists")
    screen = json.loads(args.screen.read_text())
    reference = json.loads(args.reference.read_text())
    if screen["source_id"] != reference["source_id"] or (
        screen["source_sha256"] != reference["source_sha256"]
    ):
        parser.error("Screen and reference source differ")
    result = {
        "status": "postscore_in_sample_development_not_independent_validation",
        "screen_sha256": file_sha256(args.screen),
        "reference_sha256": file_sha256(args.reference),
        "scorer_sha256": file_sha256(ROOT / "prototype/throw_event_benchmark.py"),
        "runner_sha256": file_sha256(__file__),
        "score": evaluate_events(
            screen["events"], reference["events"], reference["source_interval_s"]
        ),
        "limitations": [
            "The 2024 source and all four first-pass false candidates were inspected before assembling this screen.",
            "The reference consists of coarse, same-agent, source-only windows, not independent exhaustive labels.",
            "The lookahead, sample rate, motion rule, and one-of-three patch rule were developed in-sample.",
            "This result cannot establish cross-match precision, recall, or release-time accuracy.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        {
            key: result["score"][key]
            for key in (
                "true_positives",
                "false_positives",
                "false_negatives",
                "precision",
                "recall",
                "f1",
                "missed_reference_ids",
                "extra_prediction_ids",
            )
        }
    )


if __name__ == "__main__":
    main()
