"""Attach left board samples to the existing candidate-to-state handoff."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from candidate_state_handoff_v2 import attach_left_candidate_boards


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--left-boards", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    handoff = json.loads(args.handoff.read_text())
    boards = json.loads(args.left_boards.read_text())
    result = attach_left_candidate_boards(handoff, boards)
    result.update(
        {
            "input_sha256": {
                "candidate_state_handoff": digest(args.handoff),
                "left_candidate_partial_caps": digest(args.left_boards),
            },
            "model_code_sha256": digest(ROOT / "prototype/candidate_state_handoff_v2.py"),
            "runner_sha256": digest(Path(__file__)),
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "candidates": result["candidate_count"],
                "statuses": result["image_observation_status_counts"],
            }
        )
    )


if __name__ == "__main__":
    main()
