"""Measure exact-time Czech 1080p/360p receiving-path center agreement."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cross_resolution_path_overlap import (
    measure_all_co_sampled_pairs,
    measure_temporal_pair_overlap,
)

BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
VIDEO = BASE / "source-360p.mp4"
LEFT = BASE / "full-match-motion-merged-postscore.json"
RIGHT = BASE / "full-corridor-right-tail-first-transfer.json"
CORROB = BASE / "full-corridor-right-corrob-first-transfer.json"
OUT = BASE / "full-cross-resolution-receiving-path-overlap-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Czech overlap artifact already exists")
    left, right, corrob = (json.loads(p.read_text()) for p in (LEFT, RIGHT, CORROB))
    source_hash = digest(VIDEO)
    if (
        left["candidate_source_sha256"] != source_hash
        or right["source_sha256"] != source_hash
        or corrob["source_sha256"] != source_hash
        or corrob["input_sha256"]["right_tail"] != digest(RIGHT)
    ):
        raise ValueError("Source or candidate lineage mismatch")
    rows = measure_temporal_pair_overlap(
        left["rows"], right["directional_review_proposals"], corrob["rows"]
    )
    expected_pairs = sum(len(row["matching_right_proposals"]) for row in corrob["rows"])
    if len(rows) != expected_pairs or len(rows) != 119:
        raise ValueError("Temporal pair inventory changed")
    counts = Counter(row["sampled_time_overlap_count"] for row in rows)
    comparable = [row for row in rows if row["sampled_time_overlap_count"] >= 2]
    if len(comparable) != 42 or counts[0] != 77:
        raise ValueError("Shared-time overlap inventory changed")
    all_co_sampled = measure_all_co_sampled_pairs(
        left["rows"], right["directional_review_proposals"], corrob["rows"]
    )
    linked_controls = [row for row in all_co_sampled if row["temporal_colour_direction_link"]]
    unlinked_controls = [row for row in all_co_sampled if not row["temporal_colour_direction_link"]]
    if (
        len(all_co_sampled) != 43
        or len(linked_controls) != 42
        or len(unlinked_controls) != 1
        or {(r["left_candidate_id"], r["right_proposal_id"]) for r in linked_controls}
        != {(r["left_candidate_id"], r["right_proposal_id"]) for r in comparable}
    ):
        raise ValueError("All-pair co-sampled comparison changed")
    result = {
        "status": "cross_resolution_same_time_pixel_overlap_not_physical_identity",
        "source_video_sha256": source_hash,
        "input_sha256": {
            "left_motion": digest(LEFT),
            "right_tail": digest(RIGHT),
            "temporal_corroboration": digest(CORROB),
        },
        "model_code_sha256": digest(ROOT / "prototype/cross_resolution_path_overlap.py"),
        "runner_sha256": digest(Path(__file__)),
        "coordinate_scale_1080_to_360": 3,
        "temporal_pair_count": len(rows),
        "shared_time_sample_count_distribution": dict(sorted(counts.items())),
        "pairs_with_at_least_two_shared_samples": len(comparable),
        "pairs_without_shared_samples": counts[0],
        "all_possible_left_right_pair_count": len(left["rows"])
        * len(right["directional_review_proposals"]),
        "all_pairs_with_at_least_two_shared_samples": len(all_co_sampled),
        "co_sampled_nonlinked_control_count": len(unlinked_controls),
        "co_sampled_nonlinked_control": unlinked_controls[0],
        "median_distance_range_px_360_for_comparable_pairs": [
            min(row["median_center_distance_px_360"] for row in comparable),
            max(row["median_center_distance_px_360"] for row in comparable),
        ],
        "rows": rows,
        "all_co_sampled_pair_summary": all_co_sampled,
        "limitations": [
            "A shared source time is required; 77 temporal pairs lack exact sampled overlap and are unassessed, not mismatches.",
            "Image-center agreement can occur on people or equipment as well as stones; it is not physical stone identity or event truth.",
            "The paths are derived from related processing of the same broadcast, so this is a consistency diagnostic, not independent validation.",
            "Only one nonlinked pair shared two sampled times, so it is an illustrative control rather than a calibrated false-match distribution.",
            "The factor-three coordinate comparison assumes corresponding 1920x1080 and 640x360 full-frame images; pixel agreement does not validate metric homographies.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "pairs": len(rows),
                "overlap_ge2": len(comparable),
                "no_shared_time": counts[0],
                "median_distance_range": result[
                    "median_distance_range_px_360_for_comparable_pairs"
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
