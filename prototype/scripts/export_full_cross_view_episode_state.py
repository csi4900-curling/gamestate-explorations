"""Attach full-match partial boards to full-source cross-view candidate episodes."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cross_view_episode_state import attach_episode_partial_states


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("episodes", "corridor", "screen", "full-states", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    episodes, corridor, screen, states = (
        json.loads(getattr(args, name).read_text())
        for name in ("episodes", "corridor", "screen", "full_states")
    )
    if screen["candidates_sha256"] != digest(args.corridor) or states["input_sha256"][
        "screen"
    ] != digest(args.screen):
        raise ValueError("Full-match candidate/state input chain differs")
    decisions = screen["decisions"]
    if len({row["candidate_id"] for row in decisions}) != len(decisions):
        raise ValueError("Duplicate screen decision ID")
    reconciliation = {
        "rows": [
            {
                "interval_id": row["candidate_id"],
                "full_id": row["candidate_id"],
                "interval_accepted": row["accepted"],
                "full_accepted": row["accepted"],
                "full_status": row["status"],
            }
            for row in decisions
        ]
    }
    rows = attach_episode_partial_states(episodes, corridor, reconciliation, states)
    output = {
        "status": "full_match_cross_view_candidate_partial_state_not_throw_truth",
        "source_id": episodes["source_id"],
        "source_sha256": episodes["source_sha256"],
        "source_interval_s": episodes["source_interval_s"],
        "input_sha256": {
            name: digest(getattr(args, name))
            for name in ("episodes", "corridor", "screen", "full_states")
        },
        "model_code_sha256": digest(ROOT / "prototype/cross_view_episode_state.py"),
        "runner_sha256": digest(Path(__file__)),
        "episode_count": len(rows),
        "state_status_counts": dict(Counter(row["state_status"] for row in rows)),
        "partial_board_count": sum(
            bool(row["post_event_partial_board"] and row["post_event_partial_board"]["stones"])
            for row in rows
        ),
        "simulation_ready_count": 0,
        "episodes": rows,
        "limitations": [
            "All source candidates and right-only motion remain possible review items, not confirmed throws.",
            "Partial boards are attached by exact accepted left candidate ID only.",
            "No transition is promoted across possible unreviewed right-only events.",
            "No complete game state, metric accuracy, release/settle boundary or physical identity is verified.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {
                "episodes": len(rows),
                "partial_boards": output["partial_board_count"],
                "statuses": output["state_status_counts"],
            }
        )
    )


if __name__ == "__main__":
    main()
