"""Join every selected bidirectional source review to its frozen probe."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    review = json.loads(args.review.read_text())
    by_recording = {row["recording"]: row for row in review["sources"]}
    if len(by_recording) != len(review["sources"]):
        parser.error("Duplicate source recording")
    rows_by_key = {(row["recording"], row["raw_track_id"]): row for row in review["rows"]}
    if len(rows_by_key) != len(review["rows"]):
        parser.error("Duplicate source-review path")
    expected_keys = set()
    for name, source in by_recording.items():
        probe_path = args.directory / f"{name}-bidirectional-fast-development.json"
        manifest_path = args.directory / f"{name}-bidirectional-fast-source-review/manifest.json"
        if (
            digest(probe_path) != source["probe_sha256"]
            or digest(manifest_path) != source["source_manifest_sha256"]
        ):
            parser.error(f"Stale source review for {name}")
        probe = json.loads(probe_path.read_text())
        manifest = json.loads(manifest_path.read_text())
        if (
            probe["source_sha256"] != source["source_sha256"]
            or manifest["source_sha256"] != source["source_sha256"]
            or manifest["probe_sha256"] != digest(probe_path)
        ):
            parser.error(f"Source or probe lineage differs for {name}")
        proposal_ids = {row["raw_track_id"] for row in probe["directional_review_proposals"]}
        new_windows = set(probe["newly_covered_coarse_window_ids"])
        for row in manifest["rows"]:
            key = name, row["raw_track_id"]
            if key in expected_keys or key not in rows_by_key or key[1] not in proposal_ids:
                parser.error(f"Invalid manifest/source-review proposal {key}")
            expected_keys.add(key)
            reviewed = rows_by_key[key]
            if (
                reviewed["selection_reason"] != row["selection_reason"]
                or reviewed["coarse_window_ids"] != row["coarse_window_ids"]
            ):
                parser.error(f"Source-review selection differs for {key}")
            if row["selection_reason"] == "new_coarse_window" and not (
                new_windows & set(row["coarse_window_ids"])
            ):
                parser.error(f"Selected new-window proposal misses new window: {key}")
            if row["selection_reason"] == "outside_all_coarse_windows" and row["coarse_window_ids"]:
                parser.error(f"Outside-window proposal has a coarse match: {key}")
    if expected_keys != set(rows_by_key):
        parser.error("Review rows and rendered proposal rows differ")
    allowed = {"moving_stone_short_path", "person_wheelchair_or_clothing"}
    if any(row["source_prefix_class"] not in allowed for row in review["rows"]):
        parser.error("Unknown source-review class")
    counts = Counter(
        (row["selection_reason"], row["source_prefix_class"]) for row in review["rows"]
    )
    result = {
        "status": "selected_development_bidirectional_source_audit_not_detector_accuracy",
        "review_sha256": digest(args.review),
        "runner_sha256": digest(Path(__file__)),
        "selected_path_count": len(review["rows"]),
        "counts_by_selection_and_source_class": {
            reason: {source_class: counts[reason, source_class] for source_class in sorted(allowed)}
            for reason in ("new_coarse_window", "outside_all_coarse_windows")
        },
        "rows": review["rows"],
        "limitations": [
            "Source classes were assigned by the same development agent from three frames per selected path.",
            "Selected paths do not provide a denominator for physical throw recall or precision.",
            "A stone-colour path in a broad window can still be unrelated to that delivery.",
        ],
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["counts_by_selection_and_source_class"]))


if __name__ == "__main__":
    main()
