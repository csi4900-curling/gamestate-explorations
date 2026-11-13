"""Attach reviewed right passages as a separate, non-promoting timeline overlay."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from right_passage_timeline_overlay import build_overlay


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("timeline", "right_probe", "source_review", "output"):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    parser.add_argument("--max-lag-s", type=float, default=20)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    timeline = json.loads(args.timeline.read_text())
    probe = json.loads(args.right_probe.read_text())
    review = json.loads(args.source_review.read_text())
    if len(
        {timeline["source_sha256"], probe["source_sha256"], review["source_sha256"]}
    ) != 1 or review["probe_sha256"] != digest(args.right_probe):
        parser.error("Timeline, right probe and review provenance differs")
    start, stop = probe["source_interval_s"]
    if not (timeline["source_interval_s"][0] <= start < stop <= timeline["source_interval_s"][1]):
        parser.error("Right interval is not inside the timeline")
    left = [row for row in timeline["observed_events"] if start <= row["crossing_time_s"] <= stop]
    classes = {row["raw_track_id"]: row["source_prefix_class"] for row in review["rows"]}
    if len(classes) != len(review["rows"]):
        parser.error("Duplicate source-review IDs")
    overlay = build_overlay(
        left, probe["directional_review_proposals"], classes, max_lag_s=args.max_lag_s
    )
    result = {
        "status": "development_cross_view_passage_overlay_not_physical_event_identity",
        "source_sha256": timeline["source_sha256"],
        "source_interval_s": [start, stop],
        "max_directional_cross_view_lag_s": args.max_lag_s,
        "input_sha256": {
            "timeline": digest(args.timeline),
            "right_probe": digest(args.right_probe),
            "source_review": digest(args.source_review),
        },
        "model_code_sha256": digest(ROOT / "prototype/right_passage_timeline_overlay.py"),
        "runner_sha256": digest(Path(__file__)),
        "left_event_count_in_interval": len(left),
        "right_proposal_count": len(overlay["rows"]),
        "fusion_status_counts": dict(Counter(row["fusion_status"] for row in overlay["rows"])),
        **overlay,
        "limitations": [
            "Left events are provisional and right source classes are same-agent short-prefix reviews.",
            "For negative-y right motion the left candidate precedes the right passage; for positive-y motion it follows. This source-view ordering is a development hypothesis, not calibrated camera transit.",
            "Unique time/colour proximity does not prove one physical stone or throw.",
            "Long paths, people and ambiguous links are preserved for review, not discarded.",
            "No physical release, settle, metric trajectory, full board or simulation-ready state is inferred.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "left": len(left),
                "right": len(overlay["rows"]),
                "statuses": result["fusion_status_counts"],
            }
        )
    )


if __name__ == "__main__":
    main()
