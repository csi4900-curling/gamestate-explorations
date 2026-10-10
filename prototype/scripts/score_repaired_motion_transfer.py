"""Score a frozen repaired-motion transfer and its unchanged candidate baseline."""

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
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--screen", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Transfer score already exists")
    candidates = json.loads(args.candidates.read_text())
    screen = json.loads(args.screen.read_text())
    reference = json.loads(args.reference.read_text())
    sources = {(item["source_id"], item["source_sha256"],
                tuple(item["source_interval_s"]))
               for item in (candidates, screen, reference)}
    if len(sources) != 1 or screen["candidates_sha256"] != file_sha256(args.candidates):
        parser.error("Input source or candidate chain differs")
    candidate_ids = {event["id"] for event in candidates["events"]}
    selected_ids = {event["id"] for event in screen["events"]}
    if len(candidate_ids) != len(candidates["events"]) or (
            len(selected_ids) != len(screen["events"])) or (
            not selected_ids <= candidate_ids):
        parser.error("Screen must select unique original candidate IDs")
    scores = {
        "original_candidate_baseline": evaluate_events(
            candidates["events"], reference["events"],
            reference["source_interval_s"]),
        "fixed_repaired_motion_filter": evaluate_events(
            screen["events"], reference["events"],
            reference["source_interval_s"]),
    }
    result = {
        "status": "cross_recording_repaired_motion_development_transfer_exposed_reference",
        "source_id": reference["source_id"],
        "candidates_sha256": file_sha256(args.candidates),
        "screen_sha256": file_sha256(args.screen),
        "reference_sha256": file_sha256(args.reference),
        "scorer_sha256": file_sha256(ROOT / "prototype/throw_event_benchmark.py"),
        "runner_sha256": file_sha256(__file__),
        "scores": scores,
        "limitations": [
            "The reference and candidate set were already exposed before this transfer.",
            "Broad source-only windows assess event detection, not exact release or settle timing.",
            "The scorer records colour disagreements separately from event time matching.",
            "This same-production interval cannot establish cross-family robustness, full-match exhaustiveness, or physical stone identity.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    for name, score in scores.items():
        print(name, {key: score[key] for key in (
            "true_positives", "false_positives", "false_negatives",
            "precision", "recall", "f1", "colour_errors_among_matches")})


if __name__ == "__main__":
    main()
