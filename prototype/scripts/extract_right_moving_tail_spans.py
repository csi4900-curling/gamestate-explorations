"""Derive a provenance-preserving moving-tail review lane from right tracks."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from right_moving_tail_span import moving_tail_spans


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    probe = json.loads(args.probe.read_text())
    proposals = moving_tail_spans(probe)
    if {row["raw_track_id"] for row in proposals} != {
        row["raw_track_id"] for row in probe["directional_review_proposals"]
    }:
        raise RuntimeError("Proposal identity changed during tail extraction")
    result = {
        "status": "postscore_right_moving_tail_review_lane_not_physical_throw_identity",
        "source_sha256": probe["source_sha256"],
        "source_interval_s": probe["source_interval_s"],
        "source_time_offset_s": probe["source_time_offset_s"],
        "parent_probe_sha256": digest(args.probe),
        "model_code_sha256": digest(ROOT / "prototype/right_moving_tail_span.py"),
        "runner_sha256": digest(Path(__file__)),
        "tail_parameters": {
            "long_prefix_greater_than_s": 10,
            "maximum_tail_duration_s": 5,
            "minimum_tail_points": 3,
            "minimum_signed_step_px": 8,
            "review_span_displacement_px": 60,
        },
        "original_proposal_count": len(probe["directional_review_proposals"]),
        "directional_proposal_count": len(proposals),
        "tail_status_counts": dict(Counter(row["tail_extraction_status"] for row in proposals)),
        "directional_review_proposals": proposals,
        "limitations": [
            "The tail rule was devised after inspecting six long Estonia/Italy tracks.",
            "A short moving tail does not establish which physical stone moved or whether it was delivered.",
            "No new source observations are created; all tail points come from the parent raw track.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"proposals": len(proposals), "tail_statuses": result["tail_status_counts"]}))


if __name__ == "__main__":
    main()
