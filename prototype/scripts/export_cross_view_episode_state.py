"""Join Czechia cross-view episodes to full-match partial board evidence."""

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
    for name in (
        "episodes",
        "interval-candidates",
        "reconciliation",
        "full-states",
        "full-screen",
        "interval-screen",
        "output",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    inputs = {
        name: json.loads(getattr(args, name).read_text())
        for name in (
            "episodes",
            "interval_candidates",
            "reconciliation",
            "full_states",
            "full_screen",
            "interval_screen",
        )
    }
    reconciliation = inputs["reconciliation"]
    full_states = inputs["full_states"]
    if (
        reconciliation["input_sha256"]["full_screen"] != digest(args.full_screen)
        or reconciliation["input_sha256"]["interval_screen"] != digest(args.interval_screen)
        or full_states["input_sha256"]["screen"] != digest(args.full_screen)
        or inputs["interval_screen"]["candidates_sha256"] != digest(args.interval_candidates)
    ):
        raise ValueError("Reconciliation or state input hash chain differs")
    rows = attach_episode_partial_states(
        inputs["episodes"], inputs["interval_candidates"], reconciliation, full_states
    )
    output = {
        "status": "cross_view_episode_partial_state_handoff_not_physical_game_state",
        "source_id": inputs["episodes"]["source_id"],
        "source_sha256": inputs["episodes"]["source_sha256"],
        "source_interval_s": inputs["episodes"]["source_interval_s"],
        "input_sha256": {
            name: digest(getattr(args, name))
            for name in (
                "episodes",
                "interval_candidates",
                "reconciliation",
                "full_states",
                "full_screen",
                "interval_screen",
            )
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
            "Interval candidate IDs were reconciled to full-match IDs by the saved exact-source screen audit.",
            "A partial board belongs to one accepted candidate, not a verified physical throw episode.",
            "Right-only motion proposals and rejected left passages have no inferred outcome board.",
            "Adjacent full-match board comparisons are not promoted across this richer candidate inventory.",
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
