"""Replay saved quiet-tail detections with a stationary-suffix board rule."""

import argparse
from collections import Counter
import json
from math import dist
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from post_event_partial_board import stable_view_local_stones  # noqa: E402


def same_stone(a, b):
    return (
        a["colour"] == b["colour"]
        and dist(a["view_local_ground_position_m"], b["view_local_ground_position_m"]) <= 0.18
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boards", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Suffix audit output already exists")
    source = json.loads(args.boards.read_text())
    rows = []
    for row in source["rows"]:
        baseline = stable_view_local_stones(row["frames"])
        if baseline != row["board"]:
            raise ValueError(f"Baseline board no longer reproduces: {row['candidate_id']}")
        suffix = stable_view_local_stones(row["frames"], use_stable_suffix=True)
        missing_baseline = [
            stone
            for stone in baseline["stones"]
            if not any(same_stone(stone, new) for new in suffix["stones"])
        ]
        if missing_baseline:
            raise ValueError(f"Suffix rule lost baseline observations: {row['candidate_id']}")
        additions = [
            stone
            for stone in suffix["stones"]
            if not any(same_stone(stone, old) for old in baseline["stones"])
        ]
        rows.append(
            {
                "candidate_id": row["candidate_id"],
                "baseline_stone_count": len(baseline["stones"]),
                "suffix_stone_count": len(suffix["stones"]),
                "added_observations": additions,
                "suffix_board": suffix,
                "source_tail_last_registered_s": row["board"]["last_registered_s"],
                "source_frame_count": len(row["frames"]),
            }
        )
    output = {
        "status": "postscore_stationary_suffix_board_development_not_complete_game_state",
        "source_id": source["source_id"],
        "source_sha256": source["source_sha256"],
        "parent_boards_sha256": file_sha256(args.boards),
        "suffix_code_sha256": file_sha256(ROOT / "prototype/post_event_partial_board.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "baseline_observation_count": sum(row["baseline_stone_count"] for row in rows),
        "suffix_observation_count": sum(row["suffix_stone_count"] for row in rows),
        "addition_count_by_candidate": {
            row["candidate_id"]: len(row["added_observations"]) for row in rows
        },
        "added_colour_counts": dict(
            Counter(stone["colour"] for row in rows for stone in row["added_observations"])
        ),
        "rows": rows,
        "limitations": [
            "Rule development used the source-visible S40 omission and is not independent board validation.",
            "Suffix stability only tests temporal persistence of existing detections; it cannot detect occluded or never-proposed stones.",
            "Matching added observations to prior rows by colour and proximity does not establish physical identity.",
            "No event acceptance, complete board, score, settle time or simulation-ready state is inferred.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(
        output["baseline_observation_count"],
        "->",
        output["suffix_observation_count"],
        output["addition_count_by_candidate"],
    )


if __name__ == "__main__":
    main()
