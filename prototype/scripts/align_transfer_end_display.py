"""Attach observed 2024 end-display context to a frozen raw candidate ledger."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from end_display_context import annotate_display_context  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--marker-scan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Display-context output already exists")
    raw = json.loads(args.raw.read_text())
    scan = json.loads(args.marker_scan.read_text())
    if raw["source_sha256"] != scan["video_sha256"] or scan["video_sha256"] != file_sha256(
        Path(scan["video_path"])
    ):
        parser.error("Candidate and marker source fingerprints differ")
    ids = [row["id"] for row in raw["events"]]
    if len(ids) != len(set(ids)):
        parser.error("Duplicate raw candidate ID")
    rows = annotate_display_context(raw["events"], scan["samples"])
    if [row["event_id"] for row in rows] != ids:
        raise ValueError("Display-context candidate coverage differs")
    result = {
        "status": "source_broadcast_end_display_context_not_physical_end_assignment",
        "source_id": raw["source_id"],
        "source_sha256": raw["source_sha256"],
        "source_interval_s": raw["source_interval_s"],
        "raw_sha256": file_sha256(args.raw),
        "marker_scan_sha256": file_sha256(args.marker_scan),
        "aligner_sha256": file_sha256(ROOT / "prototype/end_display_context.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "candidate_count": len(rows),
        "context_status_counts": dict(Counter(row["display_context_status"] for row in rows)),
        "events": rows,
        "limitations": [
            "Displayed end can lag a physical delivery; no physical end is assigned.",
            "Marker changes bracket graphic updates, not exact end boundaries.",
            "Candidates are preserved regardless of their screen decision.",
            "This is source context, not independent physical-throw labels.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["context_status_counts"])


if __name__ == "__main__":
    main()
