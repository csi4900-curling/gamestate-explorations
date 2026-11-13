"""Score an exposed postscore rescue screen and unchanged candidate baseline."""

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
        parser.error("Development score already exists")
    candidates = json.loads(args.candidates.read_text())
    screen = json.loads(args.screen.read_text())
    reference = json.loads(args.reference.read_text())
    sources = {
        (item["source_id"], item["source_sha256"], tuple(item["source_interval_s"]))
        for item in (candidates, screen, reference)
    }
    if len(sources) != 1 or screen["candidates_sha256"] != file_sha256(args.candidates):
        parser.error("Input source or candidate chain differs")
    candidate_ids = {event["id"] for event in candidates["events"]}
    selected_ids = {event["id"] for event in screen["events"]}
    if (
        len(candidate_ids) != len(candidates["events"])
        or (len(selected_ids) != len(screen["events"]))
        or (not selected_ids <= candidate_ids)
    ):
        parser.error("Screen must select unique original candidate IDs")
    scores = {
        "candidate_baseline": evaluate_events(
            candidates["events"], reference["events"], reference["source_interval_s"]
        ),
        "postscore_rescue_screen": evaluate_events(
            screen["events"], reference["events"], reference["source_interval_s"]
        ),
    }
    result = {
        "status": "postscore_exposed_development_fit_not_independent_transfer",
        "source_id": reference["source_id"],
        "candidates_sha256": file_sha256(args.candidates),
        "screen_sha256": file_sha256(args.screen),
        "reference_sha256": file_sha256(args.reference),
        "scorer_sha256": file_sha256(ROOT / "prototype/throw_event_benchmark.py"),
        "runner_sha256": file_sha256(__file__),
        "scores": scores,
        "limitations": [
            "The rescue and thresholds were designed after inspecting these exposed recordings and scores.",
            "Coarse same-agent delivery windows are not independent exhaustive ground truth.",
            "This does not measure release/settle timing, full-match recall, path identity, metric accuracy, or game-state completeness.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    for name, score in scores.items():
        print(
            name,
            score["true_positives"],
            score["false_positives"],
            score["false_negatives"],
            round(score["f1"], 3),
            "colour_errors",
            score["colour_errors_among_matches"],
        )


if __name__ == "__main__":
    main()
