"""Tier pre/post cap image changes using fixed local ice-context cues."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from triage_split_partial_cap_deltas import triage_deltas


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("delta", "context", "pre", "post", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    delta, context = [json.loads(path.read_text()) for path in
                      (args.delta, args.context)]
    pre, post = [json.loads(path.read_text()) for path in (args.pre, args.post)]
    if (delta["input_sha256"]["pre_cap_scan"] != digest(args.pre)
            or delta["input_sha256"]["post_cap_scan"] != digest(args.post)
            or context["input_sha256"]["pre_cap_scan"] != digest(args.pre)
            or context["input_sha256"]["post_cap_scan"] != digest(args.post)):
        parser.error("Cap scan lineage differs")
    expected = {(event["candidate_id"], phase, item["local_observation_id"])
                for phase, scan in (("pre", pre), ("post", post))
                for event in scan["rows"] for item in event["stable_cap_proposals"]}
    observed = {(row["candidate_id"], row["phase"], row["local_observation_id"])
                for row in context["rows"]}
    if len(expected) != len(context["rows"]) or expected != observed:
        parser.error("Cap context must cover each pre/post stable cap exactly once")
    result = triage_deltas(delta, context)
    payload = {
        "status": "fixed_context_review_tiers_for_partial_image_cap_changes_not_physical_state",
        "source_sha256": delta["source_sha256"],
        "input_sha256": {"image_delta": digest(args.delta),
                         "cap_context": digest(args.context),
                         "pre_cap_scan": digest(args.pre),
                         "post_cap_scan": digest(args.post)},
        "model_code_sha256": digest(ROOT / "prototype/triage_split_partial_cap_deltas.py"),
        "runner_sha256": digest(Path(__file__)),
        **result,
        "limitations": [
            "A clear tier is a source-review priority, not evidence of a physical stone move.",
            "The context threshold was transferred from moving paths without board-specific validation.",
            "Player occlusion, handled stones, missed throws and partial field of view remain unresolved.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"candidates": result["candidate_count"],
                      "tiers": result["review_tier_counts"]}))


if __name__ == "__main__":
    main()
