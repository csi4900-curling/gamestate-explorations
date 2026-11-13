"""Export a single Latvia event and partial-state review handoff."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from episode_state_timeline import build_episode_state_timeline  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in (
        "base-handoff",
        "partial-episodes",
        "partial-boards",
        "partial-comparisons",
        "output",
    ):
        parser.add_argument(f"--{key}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    paths = {
        key: getattr(args, key.replace("-", "_"))
        for key in ("base-handoff", "partial-episodes", "partial-boards", "partial-comparisons")
    }
    inputs = {key: json.loads(path.read_text()) for key, path in paths.items()}
    base = inputs["base-handoff"]
    union = inputs["partial-episodes"]
    boards = inputs["partial-boards"]
    comparisons = inputs["partial-comparisons"]
    if (
        union["handoff_sha256"] != file_sha256(paths["base-handoff"])
        or boards["partial_episodes_sha256"] != file_sha256(paths["partial-episodes"])
        or comparisons["partial_episodes_sha256"] != file_sha256(paths["partial-episodes"])
        or comparisons["partial_boards_sha256"] != file_sha256(paths["partial-boards"])
        or any(
            doc["source_sha256"] != base["source_sha256"] for doc in (union, boards, comparisons)
        )
    ):
        parser.error("Input source or evidence chain differs")
    joined = build_episode_state_timeline(base, union, boards, comparisons)
    if (
        len(joined["candidate_timeline"]) != union["frozen_candidate_count"]
        or len(joined["event_timeline"])
        != base["event_status_counts"]["provisional_event"] + union["partial_episode_count"]
        or any(row["simulation_ready"] for row in joined["event_timeline"])
    ):
        raise ValueError("Candidate or event count differs, or simulation gate violated")
    output = {
        "status": "development_event_level_partial_state_handoff_not_validated_game_state",
        "source_id": base["source_id"],
        "source_sha256": base["source_sha256"],
        "source_interval_s": base["source_interval_s"],
        "input_sha256": {key: file_sha256(path) for key, path in paths.items()},
        "model_code_sha256": file_sha256(ROOT / "prototype/episode_state_timeline.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "candidate_count": len(joined["candidate_timeline"]),
        "frozen_event_status_counts": base["event_status_counts"],
        "event_proposal_count": len(joined["event_timeline"]),
        "event_proposal_status_counts": joined["event_proposal_status_counts"],
        "simulation_ready_count": 0,
        "candidate_timeline": joined["candidate_timeline"],
        "event_timeline": joined["event_timeline"],
        "independent_end_score_context": base["independent_end_score_context"],
        "limitations": [
            "The 14 frozen full-path proposals remain distinct from one postscore partial-prefix review proposal.",
            "Twenty-seven original passage candidates remain inspectable; grouping does not create independent physical throw labels.",
            "Partial boards and nearby observation pairs are not complete game states or persistent stone identities.",
            "Release, settle, spin, event-to-end mapping and metric accuracy are not verified.",
            "No event is ready for physical simulation or coaching claims.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(
        output["candidate_count"],
        output["event_proposal_status_counts"],
        output["simulation_ready_count"],
    )


if __name__ == "__main__":
    main()
