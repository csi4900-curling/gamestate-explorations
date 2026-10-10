"""Create a repeat-hit view of existing 2024 broadcast marker scans."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.end_marker_temporal import stable_marker_evidence


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scans", nargs="+", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first temporal summary")
    games = []
    for path in args.scans:
        scan = json.loads(path.read_text())
        if scan["status"] != "development_broadcast_graphic_evidence_not_physical_end_boundaries":
            parser.error(f"Unsupported marker scan: {path}")
        summary = stable_marker_evidence(scan["samples"])
        games.append({"video_path": scan["video_path"],
                      "video_sha256": scan["video_sha256"],
                      "scan_path": str(path), "scan_sha256": digest(path),
                      "calibrated_header_geometry": scan["calibrated_header_geometry"],
                      "sample_count": scan["sample_count"],
                      "recognized_count": scan["recognized_count"],
                      **summary})
    result = {
        "status": "development_repeated_graphic_evidence_not_end_truth",
        "summarizer_sha256": digest(ROOT / "prototype/end_marker_temporal.py"),
        "runner_sha256": digest(Path(__file__)),
        "games": games,
        "limitations": [
            "A two-hit run removes isolated optical false reads but can miss a briefly visible real marker.",
            "The active-end graphic can lag play; its transition interval is not a physical end boundary.",
            "An X in official results may still coexist with a displayed next-end marker; play status requires separate source evidence.",
            "All three recordings have been exposed during model development; this is not an independent validation score.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    for game in games:
        print(game["video_path"], [run["end"] for run in game["stable_runs"]],
              len(game["discarded_short_runs"]))


if __name__ == "__main__":
    main()
