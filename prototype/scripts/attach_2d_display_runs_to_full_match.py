"""Join versioned 2D broadcast display runs to a routed full-match timeline."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.end_marker_temporal import stable_marker_evidence
from prototype.stable_display_run_context import attach_stable_display_runs


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument("--marker-scan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve earlier result")
    timeline = json.loads(args.timeline.read_text())
    scan = json.loads(args.marker_scan.read_text())
    if (
        scan["status"] != "development_2d_registered_broadcast_marker_not_physical_end"
        or scan["video_sha256"] != timeline["source_sha256"]
    ):
        parser.error("Marker scan is not the matching source/version")
    temporal = stable_marker_evidence(scan["samples"])
    rows, counts = attach_stable_display_runs(timeline["observed_events"], temporal["stable_runs"])
    result = {
        "status": "routed_candidate_broadcast_display_context_not_physical_end_or_throw_truth",
        "source_sha256": timeline["source_sha256"],
        "timeline_sha256": digest(args.timeline),
        "marker_scan_sha256": digest(args.marker_scan),
        "temporal_summarizer_sha256": digest(ROOT / "prototype/end_marker_temporal.py"),
        "joiner_sha256": digest(ROOT / "prototype/stable_display_run_context.py"),
        "runner_sha256": digest(Path(__file__)),
        "candidate_count": len(rows),
        "context_status_counts": dict(Counter(row["display_context_status"] for row in rows)),
        "candidate_colour_claims_by_displayed_run": counts,
        "display_runs": temporal["stable_runs"],
        "discarded_short_marker_runs": temporal["discarded_short_runs"],
        "candidates": rows,
        "limitations": [
            "The first and last marker hits bound a repeated broadcast graphic, not an exact physical end.",
            "A graphic can lag the first throw of an end; candidates near transitions may be assigned the old displayed end.",
            "A candidate outside repeated marker-hit spans remains unassigned; no throw is inserted or removed.",
            "Candidate counts include false paths and misses; they are not physical deliveries or precision/recall.",
            "The source and selected marker examples were exposed during development, not independently validated.",
        ],
    }
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "candidate_count": len(rows),
                "context_status_counts": result["context_status_counts"],
                "by_displayed_run": counts,
            }
        )
    )


if __name__ == "__main__":
    main()
