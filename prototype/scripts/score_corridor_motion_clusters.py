"""Post-result diagnostic score for saved motion clusters and cap evidence."""

import argparse
from collections import Counter
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
    for name in ("candidates", "clusters", "reference", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    candidates = json.loads(args.candidates.read_text())
    clusters = json.loads(args.clusters.read_text())
    reference = json.loads(args.reference.read_text())
    if (
        clusters["candidates_sha256"] != digest(args.candidates)
        or len({candidates["source_sha256"], clusters["source_sha256"], reference["source_sha256"]})
        != 1
        or clusters["source_interval_s"] != reference["source_interval_s"]
    ):
        raise ValueError("Candidate, cluster or reference provenance differs")
    member_ids = [cid for row in clusters["rows"] for cid in row["member_ids"]]
    if len(member_ids) != len(set(member_ids)) or set(member_ids) != {
        row["id"] for row in candidates["events"]
    }:
        raise ValueError("Cluster membership does not preserve candidate IDs")
    predictions = [
        {"id": row["group_id"], "colour": row["colour"], "crossing_time_s": row["first_time_s"]}
        for row in clusters["rows"]
    ]
    score = evaluate_events(predictions, reference["events"], reference["source_interval_s"])
    matched = {item["prediction_id"] for item in score["matches"]}
    classes = []
    for row in clusters["rows"]:
        change = row.get("image_cap_delta")
        classes.append(
            {
                "group_id": row["group_id"],
                "member_ids": row["member_ids"],
                "matches_coarse_window": row["group_id"] in matched,
                "image_comparison_status": row["status"],
                "newly_observed_colour_blob_count": len(change["newly_observed"])
                if change is not None
                else None,
            }
        )
    output = {
        "status": "postscore_in_sample_cluster_review_not_detector_validation",
        "source_id": reference["source_id"],
        "source_sha256": reference["source_sha256"],
        "source_interval_s": reference["source_interval_s"],
        "reference_method": reference["reference_method"],
        "input_sha256": {
            "candidates": digest(args.candidates),
            "clusters": digest(args.clusters),
            "reference": digest(args.reference),
        },
        "scorer_code_sha256": digest(ROOT / "prototype/throw_event_benchmark.py"),
        "runner_sha256": digest(Path(__file__)),
        "score_using_first_group_observation": score,
        "matched_comparison_status_counts": dict(
            Counter(
                row["image_comparison_status"] for row in classes if row["matches_coarse_window"]
            )
        ),
        "unmatched_comparison_status_counts": dict(
            Counter(
                row["image_comparison_status"]
                for row in classes
                if not row["matches_coarse_window"]
            )
        ),
        "groups": classes,
        "limitations": [
            "The 25-second group span and image-scene rules were developed on exposed recordings.",
            "The same-agent reference is coarse and not verified exhaustive continuous-video truth.",
            "A group is a proposal unit, not a confirmed physical throw or release time.",
            "Abstaining on all unmatched groups also abstains on matched groups; no cap-based hard filter is promoted.",
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
                "matched_status": output["matched_comparison_status_counts"],
                "extra_status": output["unmatched_comparison_status_counts"],
            }
        )
    )


if __name__ == "__main__":
    main()
