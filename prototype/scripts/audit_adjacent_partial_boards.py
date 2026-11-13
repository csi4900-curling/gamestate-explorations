"""Build a view-local comparison ledger from Slovakia partial-board observations."""

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
    parser.add_argument("--boards", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--screen", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Comparison ledger already exists")
    boards = json.loads(args.boards.read_text())
    candidates = json.loads(args.candidates.read_text())
    screen = json.loads(args.screen.read_text())
    if (
        boards["candidates_sha256"] != file_sha256(args.candidates)
        or boards["screen_sha256"] != file_sha256(args.screen)
        or screen["candidates_sha256"] != file_sha256(args.candidates)
        or boards["source_id"] != candidates["source_id"]
        or boards["source_sha256"] != candidates["source_sha256"]
    ):
        parser.error("Partial-board provenance chain differs")
    accepted = [
        decision["candidate_id"] for decision in screen["decisions"] if decision["accepted"]
    ]
    rows = boards["rows"]
    if [row["candidate_id"] for row in rows] != accepted:
        parser.error("Board rows do not match screened accepted event order")
    all_candidates = sorted(
        candidates["events"] + candidates["withheld_events"], key=lambda row: row["crossing_time_s"]
    )
    comparisons = [compare_adjacent_rows(a, b, all_candidates) for a, b in zip(rows, rows[1:])]
    counts = Counter(row["status"] for row in comparisons)
    comparable = [row for row in comparisons if row["status"] == "view_local_partial_comparison"]
    output = {
        "status": "development_partial_board_comparison_not_game_state_validation",
        "source_id": boards["source_id"],
        "source_sha256": boards["source_sha256"],
        "boards_sha256": file_sha256(args.boards),
        "candidates_sha256": file_sha256(args.candidates),
        "screen_sha256": file_sha256(args.screen),
        "comparison_code_sha256": file_sha256(ROOT / "prototype" / "adjacent_partial_board.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "max_association_distance_m_conditional": 0.25,
        "comparison_status_counts": dict(counts),
        "associated_observation_pair_count": sum(
            len(row["matched_observations"]) for row in comparable
        ),
        "comparisons": comparisons,
        "limitations": [
            "Comparisons use only consecutive accepted provisional events; intervening passage candidates cause abstention.",
            "Positions are conditional, camera-local projections with unverified metric accuracy.",
            "A spatial association is not a verified persistent stone identity.",
            "Unmatched observations do not prove physical appearance, removal, or collision.",
            "End boundaries, full board completeness, and throw settle times remain unverified.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {
                "counts": dict(counts),
                "associated_pairs": output["associated_observation_pair_count"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
