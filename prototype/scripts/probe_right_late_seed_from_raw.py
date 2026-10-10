"""Replay a late-seed candidate tier on preserved right-view raw tracks."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from right_late_seed_span import late_seed_bidirectional_spans


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    source = json.loads(args.probe.read_text())
    tracks = source["raw_tracks"]
    old = {row["raw_track_id"]: row for row in source["directional_review_proposals"]}
    if len(old) != len(source["directional_review_proposals"]):
        parser.error("Duplicate original proposal")
    proposals = late_seed_bidirectional_spans(tracks)
    current = {row["raw_track_id"]: row for row in proposals}
    if not set(old) <= set(current):
        parser.error("Late seed lost original proposal")
    for raw_id, original in old.items():
        found = dict(current[raw_id])
        found.pop("seed_start_index")
        found.pop("seed_kind")
        if found != original:
            parser.error(f"Late seed changed original proposal {raw_id}")
    new = [row for row in proposals if row["raw_track_id"] not in old]
    result = {
        "status": "postscore_late_seed_development_proposals_not_accepted_throws",
        "source_sha256": source["source_sha256"],
        "source_interval_s": source["source_interval_s"],
        "source_time_offset_s": source["source_time_offset_s"],
        "original_probe_sha256": digest(args.probe),
        "late_seed_code_sha256": digest(ROOT / "prototype/right_late_seed_span.py"),
        "runner_sha256": digest(Path(__file__)),
        "original_proposal_count": len(old),
        "all_late_seed_proposal_count": len(proposals),
        "new_late_seed_proposal_count": len(new),
        "new_late_seed_proposals": new,
        "limitations": [
            "The later-seed rule was developed after inspecting Canada–USA missed coarse windows.",
            "Long raw tracks may switch object identity before the later seed.",
            "All new paths require source review; none is an accepted physical throw.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"original": len(old), "all": len(proposals), "new": len(new)}))


if __name__ == "__main__":
    main()
