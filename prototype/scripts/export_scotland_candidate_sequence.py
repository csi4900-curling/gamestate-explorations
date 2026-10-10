"""Export an ordered Scotland proposal ledger without asserting game state."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from candidate_game_state_sequence import build_candidate_sequence


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "baseline",
        "bridged",
        "bridge_triage",
        "fusion",
        "crossing_review",
        "right_source_review",
        "output",
    ):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    args = parser.parse_args()
    paths = {
        name: getattr(args, name)
        for name in (
            "baseline",
            "bridged",
            "bridge_triage",
            "fusion",
            "crossing_review",
            "right_source_review",
        )
    }
    inputs = {name: json.loads(path.read_text()) for name, path in paths.items()}
    if inputs["fusion"]["left_sha256"] != digest(paths["bridged"]):
        raise ValueError("Fusion does not use this bridged timeline")
    if inputs["bridge_triage"]["baseline_timeline_sha256"] != digest(paths["baseline"]):
        raise ValueError("Bridge triage does not use this baseline timeline")
    if inputs["bridge_triage"]["bridged_timeline_sha256"] != digest(paths["bridged"]):
        raise ValueError("Bridge triage does not use this bridged timeline")
    if inputs["crossing_review"]["bridge_triage_sha256"] != digest(paths["bridge_triage"]):
        raise ValueError("Crossing audit does not use this bridge triage")
    if inputs["crossing_review"]["bridged_fusion_sha256"] != digest(paths["fusion"]):
        raise ValueError("Crossing audit does not use this fusion output")
    result = build_candidate_sequence(
        inputs["baseline"],
        inputs["bridged"],
        inputs["bridge_triage"],
        inputs["fusion"],
        inputs["crossing_review"],
        inputs["right_source_review"],
    )
    output = {
        "status": "full_match_candidate_sequence_not_verified_throw_or_game_state",
        "source_sha256": inputs["baseline"]["source_sha256"],
        "input_sha256": {name: digest(path) for name, path in paths.items()},
        "sequence_code_sha256": digest(ROOT / "prototype/candidate_game_state_sequence.py"),
        "runner_sha256": digest(Path(__file__)),
        **result,
        "limitations": [
            "Sequence positions order visual proposals, including source-reviewed nonstones; they are not official shot numbers.",
            "The baseline's automatic acceptance is a detector decision, not a verified physical throw.",
            "Source crossing reviews were performed by the development agent on selected proposals.",
            "No candidate has a verified post-throw board, persistent stone identity, release, settle, or spin count.",
            "This ledger is a game-state evidence scaffold, not a physical simulation input.",
        ],
    }
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "candidate_sequence_count",
                    "conditional_two_view_link_count",
                    "right_only_count",
                    "evidence_tier_counts",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
