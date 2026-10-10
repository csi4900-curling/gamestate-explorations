"""Export a source-hashed full-match provisional event/partial-state sequence."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from partial_state_sequence import build_partial_state_sequence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("screen", "boards", "comparisons", "output"):
        parser.add_argument(f"--{key}", required=True, type=Path)
    parser.add_argument("--source-review", action="append", type=Path, default=[])
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; preserve first export")
    if (
        file_sha256(args.screen) != json.loads(args.boards.read_text())["screen_sha256"]
        or file_sha256(args.boards) != json.loads(args.comparisons.read_text())["boards_sha256"]
        or file_sha256(args.screen) != json.loads(args.comparisons.read_text())["screen_sha256"]
    ):
        parser.error("Evidence chain hashes differ")
    screen = json.loads(args.screen.read_text())
    boards = json.loads(args.boards.read_text())
    comparisons = json.loads(args.comparisons.read_text())
    reviews = [json.loads(path.read_text()) for path in args.source_review]
    result = build_partial_state_sequence(screen, boards, comparisons, reviews)
    result["input_sha256"] = {
        key: file_sha256(getattr(args, key)) for key in ("screen", "boards", "comparisons")
    }
    result["source_review_sha256"] = {
        review["candidate_id"]: file_sha256(path)
        for review, path in zip(reviews, args.source_review)
    }
    result["model_code_sha256"] = file_sha256(ROOT / "prototype/partial_state_sequence.py")
    result["runner_sha256"] = file_sha256(Path(__file__))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        {
            key: result[key]
            for key in (
                "event_count",
                "observed_board_count",
                "comparable_transition_count",
                "simulation_ready_count",
            )
        }
    )


if __name__ == "__main__":
    main()
