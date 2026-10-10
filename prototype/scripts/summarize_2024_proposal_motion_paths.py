"""Apply the same provisional right-view motion selector to all reference windows."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from stone_proposal_path import select_far_entry_motion_path, select_single_colour_motion_run  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposals", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--max-gap-s", type=float, required=True)
    parser.add_argument("--ids", nargs="*", help="Optional reference event IDs")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Summary artifact already exists")
    if args.max_gap_s <= 0:
        parser.error("Maximum gap must be positive")
    proposals = json.loads(args.proposals.read_text())
    reference = json.loads(args.reference.read_text())
    events = reference["events"]
    if args.ids:
        selected = set(args.ids)
        events = [event for event in events if event["id"] in selected]
        if {event["id"] for event in events} != selected:
            parser.error("Unknown reference event ID")
    rows = []
    for event in events:
        samples = [r for r in proposals["rows"] if r["reference_event_id"] == event["id"]]
        if not samples:
            parser.error(f"No proposal rows for {event['id']}")
        selection = select_single_colour_motion_run(
            samples, event["colour"], max_gap_s=args.max_gap_s
        )
        far_entry = select_far_entry_motion_path(samples, event["colour"], max_gap_s=args.max_gap_s)
        left_reverse = select_far_entry_motion_path(
            samples,
            event["colour"],
            view="left",
            max_gap_s=args.max_gap_s,
            entry_y_threshold_m=-4.5,
            forward_direction=1,
            min_samples=4,
            max_forward_speed_change_m_s=2.0,
        )
        rows.append(
            {
                "event_id": event["id"],
                "reference_colour": event["colour"],
                "reference_window_s": event["delivery_interval_s"],
                "sample_count": len(samples),
                "right_registration_abstentions": sum(
                    r["views"]["right"]["status"] == "abstained" for r in samples
                ),
                "selection": selection,
                "far_entry_selection": far_entry,
                "left_reverse_selection": left_reverse,
            }
        )
    status_counts = dict(Counter(r["selection"]["status"] for r in rows))
    far_entry_counts = dict(Counter(r["far_entry_selection"]["status"] for r in rows))
    left_reverse_counts = dict(Counter(r["left_reverse_selection"]["status"] for r in rows))
    result = {
        "status": "development_same_view_motion_path_coverage_not_event_f1",
        "source_video_sha256": proposals["source_video_sha256"],
        "proposals_sha256": file_sha256(args.proposals),
        "reference_sha256": file_sha256(args.reference),
        "selector_sha256": file_sha256(ROOT / "prototype/stone_proposal_path.py"),
        "runner_sha256": file_sha256(__file__),
        "max_gap_s": args.max_gap_s,
        "selected_reference_event_ids": [event["id"] for event in events],
        "reference_window_count": len(rows),
        "selection_status_counts": status_counts,
        "far_entry_status_counts": far_entry_counts,
        "left_reverse_status_counts": left_reverse_counts,
        "rows": rows,
        "limitations": [
            "The same agent prepared the source-only coarse windows and develops this method.",
            "This conditions on reference windows and colours; it does not detect all throws from an unseen full match.",
            "A selected same-colour motion run may belong to a different stone or a false proposal.",
            "No track here is independently validated for identity, metric accuracy, or simulation.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        {
            "unique_colour": status_counts,
            "far_entry": far_entry_counts,
            "left_reverse": left_reverse_counts,
        }
    )


if __name__ == "__main__":
    main()
