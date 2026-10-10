"""Map exposed source-prefix classes onto a widened right-entry replay.

The time/colour transfer is conditional development evidence, not labels for
physical throws or an independent validation set.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expanded", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--baseline-review", type=Path, required=True)
    parser.add_argument("--novel-review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    expanded = json.loads(args.expanded.read_text())
    baseline_scan = json.loads(args.baseline.read_text())
    baseline = json.loads(args.baseline_review.read_text())
    novel = json.loads(args.novel_review.read_text())
    source_hash = expanded["source_sha256"]
    if (
        baseline_scan["source_sha256"] != source_hash
        or digest(args.baseline) != expanded["baseline_sha256"]
        or baseline["source_sha256"] != source_hash
        or novel["source_sha256"] != source_hash
    ):
        parser.error("Review sources differ")
    labels = {row["raw_track_id"]: row["sampled_prefix_class"] for row in baseline["review"]}
    if len(labels) != len(baseline["review"]):
        parser.error("Duplicate baseline source review ID")
    baseline_by_id = {row["raw_track_id"]: row for row in baseline_scan["entry_review_proposals"]}
    if len(baseline_by_id) != len(baseline_scan["entry_review_proposals"]):
        parser.error("Duplicate baseline proposal ID")
    review = []
    for pair in expanded["time_colour_comparison"]["time_colour_pairs"]:
        if pair["crossing_time_difference_s"] > 3:
            parser.error("Loose baseline comparison pair")
        if pair["baseline_id"] not in baseline_by_id or pair["baseline_id"] not in labels:
            parser.error("Baseline pair lacks reviewed source proposal")
        review.append(
            {
                "raw_track_id": pair["expanded_id"],
                "sampled_prefix_class": labels[pair["baseline_id"]],
                "class_provenance": "conditional_time_colour_baseline_review_transfer",
                "baseline_raw_track_id": pair["baseline_id"],
                "physical_throw_verified": False,
            }
        )
    for row in novel["review"]:
        review.append(
            {
                "raw_track_id": row["raw_track_id"],
                "sampled_prefix_class": row["sampled_prefix_class"],
                "class_provenance": "same_agent_selected_source_strip_review",
                "baseline_raw_track_id": None,
                "physical_throw_verified": False,
            }
        )
    expected = {row["raw_track_id"] for row in expanded["entry_review_proposals"]}
    actual = [row["raw_track_id"] for row in review]
    if len(set(actual)) != len(actual) or set(actual) != expected:
        parser.error("Transferred review does not cover each expanded prefix once")
    output = {
        "status": "conditional_development_prefix_classes_not_independent_throw_labels",
        "source_sha256": source_hash,
        "variant_sha256": digest(args.expanded),
        "input_sha256": {
            "baseline": digest(args.baseline),
            "baseline_review": digest(args.baseline_review),
            "novel_review": digest(args.novel_review),
        },
        "runner_sha256": digest(Path(__file__)),
        "review_count": len(review),
        "review": sorted(review, key=lambda row: row["raw_track_id"]),
        "limitations": [
            "Baseline classes are carried through time/colour proposal pairs, not re-reviewed as physical identities.",
            "Novel classes came from same-agent selected source strips.",
            "These are neither independent event labels nor complete physical throw windows.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"review_rows": len(review)}))


if __name__ == "__main__":
    main()
