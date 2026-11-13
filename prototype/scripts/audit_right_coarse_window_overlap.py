"""Reproduce conditional right-proposal overlap with same-agent coarse windows.

This is a development coverage audit, not a physical throw recall scorer.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def overlaps(reference_events, proposals, source_classes):
    rows = []
    for event in reference_events:
        start, stop = event["delivery_interval_s"]
        matches = [
            proposal["raw_track_id"]
            for proposal in proposals
            if proposal["colour_claim"] == event["colour"]
            and start <= proposal["passage"]["time_s"] <= stop
            and source_classes[proposal["raw_track_id"]]
            in ("moving_stone", "stone_pixels_identity_uncertain")
        ]
        rows.append(
            {
                "coarse_window_id": event["id"],
                "colour": event["colour"],
                "delivery_interval_s": [start, stop],
                "reviewed_stone_pixel_proposal_ids": matches,
            }
        )
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("reference", "probe", "source_review", "output"):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    reference = json.loads(args.reference.read_text())
    probe = json.loads(args.probe.read_text())
    review = json.loads(args.source_review.read_text())
    if (
        reference["source_sha256"] != probe["source_sha256"]
        or review["source_sha256"] != probe["source_sha256"]
        or review["probe_sha256"] != digest(args.probe)
    ):
        parser.error("Source, probe and review provenance differs")
    proposals = probe["directional_review_proposals"]
    classes = {row["raw_track_id"]: row["source_prefix_class"] for row in review["rows"]}
    ids = [row["raw_track_id"] for row in proposals]
    if len(classes) != len(review["rows"]) or len(ids) != len(set(ids)) or set(classes) != set(ids):
        parser.error("Source review must cover every distinct proposal")
    rows = overlaps(reference["events"], proposals, classes)
    result = {
        "status": "conditional_same_agent_coarse_window_stone_pixel_overlap_not_throw_recall",
        "source_sha256": probe["source_sha256"],
        "reference_sha256": digest(args.reference),
        "probe_sha256": digest(args.probe),
        "source_review_sha256": digest(args.source_review),
        "runner_sha256": digest(Path(__file__)),
        "coarse_window_count": len(rows),
        "windows_with_stone_pixel_proposal": sum(
            bool(row["reviewed_stone_pixel_proposal_ids"]) for row in rows
        ),
        "rows": rows,
        "limitations": [
            "Coarse windows and source classes are same-agent development reviews.",
            "A passage time inside a broad window does not verify physical delivery identity.",
            "The reference is not an exhaustive independent event denominator; this is not recall or F1.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {"overlap": result["windows_with_stone_pixel_proposal"], "coarse_windows": len(rows)}
        )
    )


if __name__ == "__main__":
    main()
