"""Export a conserved full-match Czech candidate and partial-state handoff."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from full_match_evidence_union import build_evidence_union


def digest(path):
    result = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("raw", "screen", "sequence", "prefixes", "prefix_boards",
                 "right_links", "right_review", "output"):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    paths = {name: getattr(args, name) for name in (
        "raw", "screen", "sequence", "prefixes", "prefix_boards",
        "right_links", "right_review")}
    inputs = {name: json.loads(path.read_text()) for name, path in paths.items()}
    if (inputs["sequence"]["input_sha256"]["screen"] != digest(args.screen) or
            inputs["prefix_boards"]["proposals_sha256"] != digest(args.prefixes) or
            inputs["right_review"]["variant_sha256"] !=
            inputs["right_links"]["right_sha256"]):
        parser.error("Input lineage fingerprints differ")
    union = build_evidence_union(**inputs)
    output = {
        "status": "development_full_match_evidence_union_not_throw_truth_or_game_state",
        "source_id": inputs["raw"]["source_id"],
        "source_sha256": inputs["raw"]["source_sha256"],
        "source_interval_s": inputs["raw"]["source_interval_s"],
        "input_sha256": {name: digest(path) for name, path in paths.items()},
        "model_code_sha256": digest(ROOT / "prototype/full_match_evidence_union.py"),
        "runner_sha256": digest(Path(__file__)),
        **union,
        "limitations": [
            "The 91 accepted screen paths and six pre-split paths are provisional and not 97 verified throws.",
            "S96 and S143 remain in the 91 accepted screen rows but carry agent-reviewed false-path flags.",
            "The five unmatched right prefixes were agent-reviewed as people or wheelchairs, not independently labelled.",
            "Partial stable boards are neither complete nor independently stone-validated.",
            "No independent exhaustive labels, physical event boundaries, metric error bounds, persistent identities or simulation-ready states are supplied.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"raw": union["raw_trigger_count"],
                      "tiers": union["candidate_tier_counts"],
                      "partial_boards": union["partial_board_count"],
                      "right_links": union["conditional_right_link_count"],
                      "unmatched_right": union["unmatched_right_review_count"]}))


if __name__ == "__main__":
    main()
