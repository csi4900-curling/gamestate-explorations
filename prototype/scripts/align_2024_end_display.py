"""Align provisional throw candidates to local 2024 broadcast end displays."""

import argparse
from bisect import bisect_right
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.end_display_context import annotate_display_context


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument("--marker-scan", type=Path, required=True)
    parser.add_argument("--temporal-summary", type=Path, required=True)
    parser.add_argument("--boundary-audit", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first alignment")
    timeline = json.loads(args.timeline.read_text())
    scan = json.loads(args.marker_scan.read_text())
    summary = json.loads(args.temporal_summary.read_text())
    if timeline["source_id"] not in scan["video_path"]:
        parser.error("Timeline and marker scan identify different videos")
    game = next(
        (row for row in summary["games"] if row["video_sha256"] == scan["video_sha256"]), None
    )
    if game is None or game["scan_sha256"] != digest(args.marker_scan):
        parser.error("Temporal summary does not refer to this exact scan")
    excluded_times = [
        row["first_hit_s"] for row in game["discarded_short_runs"] if row["hit_count"] == 1
    ]
    rows = annotate_display_context(
        timeline["observed_events"], scan["samples"], ignored_marker_times_s=excluded_times
    )
    result = {
        "status": "development_display_context_not_physical_end_assignment",
        "source_id": timeline["source_id"],
        "timeline_path": str(args.timeline),
        "timeline_sha256": digest(args.timeline),
        "marker_scan_path": str(args.marker_scan),
        "marker_scan_sha256": digest(args.marker_scan),
        "temporal_summary_path": str(args.temporal_summary),
        "temporal_summary_sha256": digest(args.temporal_summary),
        "aligner_sha256": digest(ROOT / "prototype/end_display_context.py"),
        "runner_sha256": digest(Path(__file__)),
        "ignored_isolated_marker_times_s": excluded_times,
        "event_count": len(rows),
        "context_status_counts": dict(Counter(row["display_context_status"] for row in rows)),
        "events": rows,
        "limitations": [
            "Displayed end is not physical end; the graphic can lag the first throw.",
            "Only markers within 30 s on both sides of an event can supply a displayed end.",
            "A missing marker leaves the event's display context unknown, not a missing throw.",
            "No event candidate is inserted, removed, recoloured or reassigned to a physical end.",
        ],
    }
    if args.boundary_audit:
        audit = json.loads(args.boundary_audit.read_text())
        boundaries = audit["boundary_review_times_s"]
        excluded_ids = set(audit["source_reviewed_likely_nonstone_event_ids"])
        assessed = [
            row
            for row in rows
            if row["displayed_end"] is not None and row["event_id"] not in excluded_ids
        ]
        disagreements = [
            {
                "event_id": row["event_id"],
                "crossing_time_s": row["crossing_time_s"],
                "displayed_end": row["displayed_end"],
                "source_reviewed_end": bisect_right(boundaries, row["crossing_time_s"]) + 1,
            }
            for row in assessed
            if row["displayed_end"] != bisect_right(boundaries, row["crossing_time_s"]) + 1
        ]
        result["source_reviewed_boundary_comparison"] = {
            "boundary_audit_path": str(args.boundary_audit),
            "boundary_audit_sha256": digest(args.boundary_audit),
            "reviewed_events_with_display_context": len(assessed),
            "display_vs_source_end_disagreements": disagreements,
            "interpretation": "A disagreement can reflect broadcast-graphic lag; it is not automatically a wrong throw or wrong source review.",
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        args.output,
        result["context_status_counts"],
        len(
            result.get("source_reviewed_boundary_comparison", {}).get(
                "display_vs_source_end_disagreements", []
            )
        ),
    )


if __name__ == "__main__":
    main()
