"""Replay a line-free right-span recall tier on preserved 2024 tracks."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from right_view_span_fallback import span_fallback


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def covering_windows(proposals, reference, *, passage_key):
    return {
        event["id"]
        for event in reference["events"]
        for proposal in proposals
        if proposal["colour_claim"] == event["colour"]
        and event["delivery_interval_s"][0]
        <= proposal[passage_key]["time_s"]
        <= event["delivery_interval_s"][1]
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("transfer", "variant", "reference", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    transfer = json.loads(args.transfer.read_text())
    variant = json.loads(args.variant.read_text())
    reference = json.loads(args.reference.read_text())
    source_hash = transfer["source_sha256"]
    if (
        variant["source_sha256"] != source_hash
        or reference["source_sha256"] != source_hash
        or variant["source_transfer_sha256"] != digest(args.transfer)
    ):
        parser.error("Transfer, variant and reference provenance differs")
    if (
        reference["source_interval_s"] != transfer["source_interval_s"]
        or variant["source_interval_s"] != transfer["source_interval_s"]
    ):
        parser.error("Source intervals differ")
    prior = variant["entry_review_proposals"]
    prior_ids = [row["raw_track_id"] for row in prior]
    added = span_fallback(transfer["raw_tracks"], prior_ids)
    prior_windows = covering_windows(prior, reference, passage_key="entry_crossing")
    added_windows = covering_windows(added, reference, passage_key="passage")
    all_windows = {row["id"] for row in reference["events"]}
    result = {
        "status": "postreview_line_free_right_span_recall_probe_not_event_detector",
        "source_id": transfer["source_id"],
        "source_sha256": source_hash,
        "source_interval_s": transfer["source_interval_s"],
        "transfer_sha256": digest(args.transfer),
        "variant_sha256": digest(args.variant),
        "coarse_reference_sha256": digest(args.reference),
        "fallback_code_sha256": digest(ROOT / "prototype/right_view_span_fallback.py"),
        "runner_sha256": digest(Path(__file__)),
        "rule": {
            "first_cap_area_at_least_px2": 12,
            "first_bbox_width_at_least_height": True,
            "upward_displacement_at_least_px": 60,
            "maximum_observed_delay_s": 20,
            "passage_time_semantics": "halfway_observed_upward_motion_span_not_fixed_line",
        },
        "existing_variant_prefix_count": len(prior),
        "additional_span_prefix_count": len(added),
        "coarse_window_count": len(all_windows),
        "coarse_windows_with_existing_variant_prefix": sorted(prior_windows),
        "coarse_windows_with_added_span_prefix": sorted(added_windows),
        "newly_covered_coarse_window_ids": sorted(added_windows - prior_windows),
        "still_uncovered_coarse_window_ids": sorted(all_windows - prior_windows - added_windows),
        "additional_span_review_proposals": added,
        "limitations": [
            "This fallback was designed after inspecting missed development windows on these recordings.",
            "A same-colour passage inside a coarse window can be a person or equipment; no source identity is inferred.",
            "The five-second-still reference is not independently certified or exhaustive; window coverage is not recall.",
            "This tier adds review proposals and does not change accepted events, precision, recall or F1.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "prior": len(prior),
                "added": len(added),
                "newly_covered": result["newly_covered_coarse_window_ids"],
                "still_uncovered": result["still_uncovered_coarse_window_ids"],
            }
        )
    )


if __name__ == "__main__":
    main()
