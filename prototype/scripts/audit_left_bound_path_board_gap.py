"""Measure conditional distance from each added path end to same-colour board proposals."""

import argparse
from hashlib import sha256
import json
from math import dist
from pathlib import Path


def digest(path):
    value = sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--boards", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    batch = json.loads(args.batch.read_text())
    boards = json.loads(args.boards.read_text())
    by_board = {row["candidate_id"]: row for row in boards["rows"]}
    if (
        len(by_board) != len(boards["rows"])
        or set(by_board) != set(batch["changed_selection_ids"])
        or boards["high_resolution_source_sha256"] != batch["video_sha256"]
    ):
        parser.error("Added boards and paired paths differ")
    rows = []
    for pid in batch["changed_selection_ids"]:
        paired_path = args.batch.parent / f"{pid.lower()}-paired.json"
        paired = json.loads(paired_path.read_text())
        path = paired["cases"]["extended"]["selection"]["path"]
        board = by_board[pid]
        if (
            paired["candidate_id"] != pid
            or paired["colour"] != board["colour"]
            or board["receiving_view"] != "left"
            or not path
            or board["board"]["status"] != "partial_stable_view_local_board"
        ):
            raise ValueError(f"Invalid path/board pair {pid}")
        last = path[-1]
        proposals = [
            stone for stone in board["board"]["stones"] if stone["colour"] == board["colour"]
        ]
        nearest = min(
            (
                (dist(last["ground_position_m"], stone["view_local_ground_position_m"]), stone)
                for stone in proposals
            ),
            key=lambda item: item[0],
            default=None,
        )
        rows.append(
            {
                "candidate_id": pid,
                "paired_path_sha256": digest(paired_path),
                "candidate_colour": board["colour"],
                "path_last_observed_s": last["source_time_s"],
                "path_last_conditional_position_m": last["ground_position_m"],
                "stable_same_colour_board_proposal_count": len(proposals),
                "nearest_same_colour_board_observation_id": nearest[1]["local_observation_id"]
                if nearest
                else None,
                "nearest_distance_m_conditional": round(nearest[0], 4) if nearest else None,
                "physical_identity_verified": False,
                "simulation_ready": False,
            }
        )
    result = {
        "status": "postscore_path_endpoint_to_partial_board_gap_not_identity",
        "batch_sha256": digest(args.batch),
        "boards_sha256": digest(args.boards),
        "runner_sha256": digest(Path(__file__)),
        "row_count": len(rows),
        "rows": rows,
        "limitations": [
            "Positions are conditional same-view projections without independently measured metric error.",
            "The stone can keep travelling or collide after the observed path ends; nearest board proposal need not be its endpoint.",
            "A short distance alone does not prove physical stone identity or settle time.",
        ],
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(len(rows), "path-to-board diagnostics")


if __name__ == "__main__":
    main()
