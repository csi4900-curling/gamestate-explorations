"""Export early right-view entry proposals without changing event decisions."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from right_view_entry_triage import triage_tracks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    probe = json.loads(args.probe.read_text())
    intervals = []
    for row in probe["intervals"]:
        tracks = row["tracks"]
        if len({track["track_id"] for track in tracks}) != len(tracks):
            raise ValueError("Duplicate raw track ID within interval")
        proposals = triage_tracks(tracks)
        chosen = {item["raw_track_id"] for item in proposals}
        intervals.append(
            {
                "interval_s": row["interval_s"],
                "raw_track_count": len(tracks),
                "entry_review_count": len(proposals),
                "unpromoted_raw_track_count": len(tracks) - len(proposals),
                "entry_review_proposals": proposals,
                "unpromoted_raw_track_ids": [
                    track["track_id"] for track in tracks if track["track_id"] not in chosen
                ],
            }
        )
    output = {
        "status": "postreview_development_right_entry_proposals_not_throw_truth",
        "source_sha256": probe["source_sha256"],
        "probe_sha256": file_sha256(args.probe),
        "triage_code_sha256": file_sha256(ROOT / "prototype/right_view_entry_triage.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "entry_line_y_px": 250,
        "intervals": intervals,
        "limitations": [
            "The contour and crossing thresholds were chosen after inspecting Latvia source-selected tracks.",
            "An entry-line crossing is an image observation, not a physical release or verified delivery.",
            "A true throw can be occluded or first appear beyond the line; unpromoted tracks remain available for review.",
            "The apparent track may switch physical identity after the short prefix.",
            "No event decision or precision/recall/F1 claim changes.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print([(row["raw_track_count"], row["entry_review_count"]) for row in intervals])


if __name__ == "__main__":
    main()
