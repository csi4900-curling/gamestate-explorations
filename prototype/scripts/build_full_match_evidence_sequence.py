"""Export a provenance-checked candidate sequence from two-view inventories."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from full_match_evidence_sequence import build_sequence


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("timeline", "inventory", "context", "left_review", "output"):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    parser.add_argument(
        "--right-review", nargs=2, action="append", required=True, metavar=("RUN_ID", "REVIEW_JSON")
    )
    parser.add_argument("--rescue", type=Path)
    parser.add_argument("--rescue-source-probe", type=Path)
    parser.add_argument("--rescue-review", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    timeline, inventory, context = [
        read(path) for path in (args.timeline, args.inventory, args.context)
    ]
    if inventory["timeline_sha256"] != digest(args.timeline):
        parser.error("Inventory timeline provenance differs")
    if context["inventory_sha256"] != digest(args.inventory):
        parser.error("Context inventory provenance differs")
    if args.rescue:
        rescue = read(args.rescue)
        if rescue["timeline_sha256"] != digest(args.timeline) or rescue[
            "inventory_sha256"
        ] != digest(args.inventory):
            parser.error("Targeted raw-motion provenance differs")
    else:
        rescue = None
    reviews = {}
    review_paths = {}
    for run_id, raw_path in args.right_review:
        path = Path(raw_path)
        if run_id in reviews:
            parser.error("Repeated right-review run")
        reviews[run_id] = read(path)
        review_paths[run_id] = path
    if set(reviews) != {row["id"] for row in inventory["supported_runs"]}:
        parser.error("Exactly one disagreement review per supported run required")
    if args.rescue_review:
        if not args.rescue or not args.rescue_source_probe:
            parser.error("Rescue review requires rescue and flattened source probe")
        source_probe = read(args.rescue_source_probe)
        if source_probe["targeted_probe_sha256"] != digest(args.rescue) or read(args.rescue_review)[
            "probe_sha256"
        ] != digest(args.rescue_source_probe):
            parser.error("Rescue source review provenance differs")
    elif args.rescue_source_probe:
        parser.error("Rescue source probe requires its source review")
    result = build_sequence(
        timeline,
        inventory,
        context,
        reviews,
        read(args.left_review),
        rescue,
        read(args.rescue_review) if args.rescue_review else None,
    )
    payload = {
        "status": "ordered_full_match_candidate_evidence_not_verified_throw_sequence",
        "source_id": timeline["source_id"],
        "input_sha256": {
            "timeline": digest(args.timeline),
            "inventory": digest(args.inventory),
            "context": digest(args.context),
            "left_review": digest(args.left_review),
            "right_reviews_by_run": {key: digest(path) for key, path in review_paths.items()},
            "targeted_rescue": digest(args.rescue) if args.rescue else None,
            "targeted_rescue_source_probe": digest(args.rescue_source_probe)
            if args.rescue_source_probe
            else None,
            "targeted_rescue_review": digest(args.rescue_review) if args.rescue_review else None,
        },
        "model_code_sha256": digest(ROOT / "prototype/full_match_evidence_sequence.py"),
        "runner_sha256": digest(Path(__file__)),
        **result,
        "limitations": [
            "Source classes are same-agent sparse-frame reviews, not exhaustive physical throw labels.",
            "Temporal links do not prove a stone is the same physical object across cameras.",
            "Targeted relaxed raw paths, when present, were searched only near existing left-only events.",
            "Coverage gaps and unobserved throws remain unknown.",
            "No row is promoted to a complete board or simulation-ready state.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(
        json.dumps(
            {
                "rows": result["sequence_row_count"],
                "left": result["left_candidate_count"],
                "right_only": result["right_only_count"],
                "tiers": result["evidence_tier_counts"],
            }
        )
    )


if __name__ == "__main__":
    main()
