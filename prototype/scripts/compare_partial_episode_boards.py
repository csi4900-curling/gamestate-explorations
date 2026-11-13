"""Compare review-episode boards with neighboring accepted partial boards."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from adjacent_partial_board import compare_adjacent_rows  # noqa: E402
from cache_contract import file_sha256  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in (
        "partial-boards",
        "accepted-boards",
        "partial-episodes",
        "candidates",
        "screen",
        "output",
    ):
        parser.add_argument(f"--{key}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    partial = json.loads(args.partial_boards.read_text())
    accepted = json.loads(args.accepted_boards.read_text())
    union = json.loads(args.partial_episodes.read_text())
    candidates = json.loads(args.candidates.read_text())
    screen = json.loads(args.screen.read_text())
    if (
        partial["partial_episodes_sha256"] != file_sha256(args.partial_episodes)
        or partial["candidates_sha256"] != file_sha256(args.candidates)
        or accepted["candidates_sha256"] != file_sha256(args.candidates)
        or accepted["screen_sha256"] != file_sha256(args.screen)
        or screen["candidates_sha256"] != file_sha256(args.candidates)
        or union["source_sha256"] != candidates["source_sha256"]
        or partial["source_sha256"] != candidates["source_sha256"]
        or accepted["source_sha256"] != candidates["source_sha256"]
    ):
        parser.error("Partial and accepted board evidence does not chain")
    by_partial = {row["episode_id"]: row for row in partial["rows"]}
    if len(by_partial) != len(partial["rows"]) or set(by_partial) != {
        row["episode_id"] for row in union["episodes"]
    }:
        parser.error("Partial board rows do not match episodes")
    event_rows = candidates["events"] + candidates["withheld_events"]
    accepted_rows = sorted(accepted["rows"], key=lambda row: row["crossing_time_s"])
    comparisons = []
    for episode in union["episodes"]:
        row = by_partial[episode["episode_id"]]
        cue = min(episode["candidate_passage_times_s"].values())
        pseudo = {
            "candidate_id": episode["episode_id"],
            "crossing_time_s": cue,
            "receiving_view": row["receiving_view"],
            "board": row["board"],
        }
        # Members are the same proposed episode, not intervening shots.
        other_candidates = [
            event for event in event_rows if event["id"] not in episode["candidate_ids"]
        ]
        previous = next(
            (
                accepted_row
                for accepted_row in reversed(accepted_rows)
                if accepted_row["crossing_time_s"] < cue
            ),
            None,
        )
        following = next(
            (
                accepted_row
                for accepted_row in accepted_rows
                if accepted_row["crossing_time_s"] > cue
            ),
            None,
        )
        for direction, before, after in (
            ("from_previous_accepted", previous, pseudo),
            ("to_next_accepted", pseudo, following),
        ):
            if before is None or after is None:
                comparisons.append(
                    {
                        "episode_id": episode["episode_id"],
                        "direction": direction,
                        "status": "abstain_no_neighboring_accepted_board",
                    }
                )
                continue
            compared = compare_adjacent_rows(before, after, other_candidates)
            comparisons.append(
                {
                    "episode_id": episode["episode_id"],
                    "direction": direction,
                    "excluded_same_episode_candidate_ids": episode["candidate_ids"],
                    **compared,
                }
            )
    counts = dict(Counter(row["status"] for row in comparisons))
    result = {
        "status": "postscore_partial_episode_board_comparison_not_game_state_validation",
        "source_id": candidates["source_id"],
        "source_sha256": candidates["source_sha256"],
        "partial_boards_sha256": file_sha256(args.partial_boards),
        "accepted_boards_sha256": file_sha256(args.accepted_boards),
        "partial_episodes_sha256": file_sha256(args.partial_episodes),
        "candidates_sha256": file_sha256(args.candidates),
        "screen_sha256": file_sha256(args.screen),
        "comparison_code_sha256": file_sha256(ROOT / "prototype/adjacent_partial_board.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "comparison_status_counts": counts,
        "associated_observation_pair_count": sum(
            len(row.get("matched_observations", [])) for row in comparisons
        ),
        "comparisons": comparisons,
        "limitations": [
            "Same-episode passage cues are excluded only from the intervening-candidate test; grouping is not verified physical identity.",
            "Intervening unassociated passage candidates force abstention, even if they later prove false.",
            "View-local spatial associations are not persistent stone identities or physical appearance/removal claims.",
            "End identity, complete board state and simulator-ready positions remain unverified.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(counts, result["associated_observation_pair_count"])


if __name__ == "__main__":
    main()
