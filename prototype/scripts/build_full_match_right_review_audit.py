"""Join source reviews with the complete right/left temporal inventory."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from full_match_right_review_audit import audit


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("inventory", "context", "left_review", "matched_cluttered_review", "output"):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    parser.add_argument(
        "--right-review", nargs=2, action="append", metavar=("RUN_ID", "REVIEW"), required=True
    )
    parser.add_argument("--matched-clear-sample", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    inventory = json.loads(args.inventory.read_text())
    context = json.loads(args.context.read_text())
    if context["source_sha256"] != inventory["source_sha256"] or context[
        "inventory_sha256"
    ] != digest(args.inventory):
        parser.error("Context and inventory lineage differs")
    reviews = []
    hashes = {}
    for run_id, path_str in args.right_review:
        path = Path(path_str)
        review = json.loads(path.read_text())
        if run_id in hashes or review["source_sha256"] != inventory["source_sha256"]:
            parser.error("Duplicate run or source mismatch")
        reviews.append((run_id, review))
        hashes[run_id] = digest(path)
    if set(hashes) != set(inventory["right_probe_sha256_by_run"]):
        parser.error("One right review per supported run required")
    other = {}
    for name in ("left_review", "matched_cluttered_review", "matched_clear_sample"):
        path = getattr(args, name)
        if path is not None:
            other[name] = json.loads(path.read_text())
            if other[name]["source_sha256"] != inventory["source_sha256"]:
                parser.error(f"{name} source differs")
    result = audit(
        inventory,
        context,
        reviews,
        other["left_review"],
        other["matched_cluttered_review"],
        other.get("matched_clear_sample"),
    )
    payload = {
        "status": "same_agent_full_match_disagreement_source_review_not_event_accuracy",
        "source_sha256": inventory["source_sha256"],
        "inventory_sha256": digest(args.inventory),
        "context_sha256": digest(args.context),
        "right_review_sha256_by_run": hashes,
        "other_review_sha256": {name: digest(getattr(args, name)) for name in other},
        "model_code_sha256": digest(ROOT / "prototype/full_match_right_review_audit.py"),
        "runner_sha256": digest(Path(__file__)),
        **result,
        "limitations": [
            "The reviews were made by the developer from sparse source sheets, not independent exhaustive labels.",
            "Time/colour matching and clear context are not physical throw or stone identity proof.",
            "The matched-clear sample cannot estimate full-match precision.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
