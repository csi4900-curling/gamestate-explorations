"""Export an ordered candidate-to-partial-image-state handoff with provenance."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from candidate_state_handoff import attach_candidate_states


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--union", required=True, type=Path)
    parser.add_argument("--right-boards", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    union = json.loads(args.union.read_text())
    boards = json.loads(args.right_boards.read_text())
    result = attach_candidate_states(union, boards)
    result["input_sha256"] = {
        "candidate_review_union": file_sha256(args.union),
        "right_only_partial_caps": file_sha256(args.right_boards),
    }
    result["model_code_sha256"] = file_sha256(ROOT / "prototype/candidate_state_handoff.py")
    result["runner_sha256"] = file_sha256(Path(__file__))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as file:
        file.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "candidates": result["candidate_count"],
                "image_statuses": result["image_observation_status_counts"],
            }
        )
    )


if __name__ == "__main__":
    main()
