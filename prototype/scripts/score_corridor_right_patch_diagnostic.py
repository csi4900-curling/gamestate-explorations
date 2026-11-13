"""Postreview scoring of a strict two-view and three-patch diagnostic gate."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.throw_event_benchmark import evaluate_events


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("candidates", "corroboration", "patches", "reference", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    candidates = json.loads(args.candidates.read_text())
    corroboration = json.loads(args.corroboration.read_text())
    patches = json.loads(args.patches.read_text())
    reference = json.loads(args.reference.read_text())
    if (
        len({x["source_sha256"] for x in (candidates, corroboration, patches, reference)}) != 1
        or candidates["source_interval_s"] != reference["source_interval_s"]
        or corroboration["input_sha256"]["left"] != digest(args.candidates)
        or patches["input_sha256"]["corroboration"] != digest(args.corroboration)
    ):
        raise ValueError("Source or input lineage differs")
    by_left = {row["left_candidate_id"]: row for row in corroboration["rows"]}
    by_right = {row["right_proposal_id"]: row for row in patches["rows"]}
    if (
        len(by_left) != len(corroboration["rows"])
        or len(by_right) != len(patches["rows"])
        or set(by_left) != {row["id"] for row in candidates["events"]}
    ):
        raise ValueError("Candidate coverage differs")
    selected = []
    for candidate in candidates["events"]:
        joined = by_left[candidate["id"]]
        if joined["corroboration_tier"] != "unique_right_time_colour_direction_candidate":
            continue
        right_id = joined["unique_right_candidate_ids"][0]
        patch = by_right[right_id]
        if patch["scored_count"] == 3 and patch["positive_patch_count"] == 3:
            selected.append(candidate)
    score = evaluate_events(selected, reference["events"], reference["source_interval_s"])
    output = {
        "status": "postscore_exposed_development_diagnostic_not_frozen_detector",
        "source_id": reference["source_id"],
        "source_sha256": reference["source_sha256"],
        "source_interval_s": reference["source_interval_s"],
        "input_sha256": {
            name: digest(getattr(args, name))
            for name in ("candidates", "corroboration", "patches", "reference")
        },
        "scorer_code_sha256": digest(ROOT / "prototype/throw_event_benchmark.py"),
        "runner_sha256": digest(Path(__file__)),
        "rule": "unique right temporal match and three of three frozen-model patch positives",
        "selected_candidate_ids": [row["id"] for row in selected],
        "hypothetical_score": score,
        "limitations": [
            "The three-of-three rule was inspected on these exposed clips; this is in-sample scoring.",
            "Coarse same-agent reference windows are not independently exhaustive.",
            "Patch appearance does not establish a throw or cross-camera physical identity.",
            "No full-match or unseen-family event F1 is established.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {
                "source": output["source_id"],
                "tp": score["true_positives"],
                "fp": score["false_positives"],
                "fn": score["false_negatives"],
            }
        )
    )


if __name__ == "__main__":
    main()
