"""Replay threshold variant on preserved active-right/static-left raw tracks."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from right_view_entry_triage import triage_tracks
from probe_right_entry_235_225 import variant


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    motion = json.loads(args.motion.read_text())
    baseline = json.loads(args.baseline.read_text())
    if motion["source_sha256"] != baseline["source_sha256"]:
        parser.error("Source fingerprints differ")
    intervals = []
    for m, b in zip(motion["intervals"], baseline["intervals"], strict=True):
        if m["interval_s"] != b["interval_s"]:
            parser.error("Interval fingerprints differ")
        tracks = m["tracks"]
        frozen = [row["raw_track_id"] for row in b["entry_review_proposals"]]
        if [row["raw_track_id"] for row in triage_tracks(tracks)] != frozen:
            parser.error("Frozen baseline no longer reproduces")
        rows = variant(tracks)
        ids = {row["raw_track_id"] for row in rows}
        intervals.append({"interval_s": m["interval_s"],
                          "raw_track_count": len(tracks),
                          "baseline_ids": frozen,
                          "baseline_ids_lost": [id for id in frozen if id not in ids],
                          "new_ids": [row["raw_track_id"] for row in rows
                                      if row["raw_track_id"] not in frozen],
                          "entry_review_proposals": rows})
    result = {
        "status": "postreview_threshold_variant_static_left_transfer_not_accepted_events",
        "source_sha256": motion["source_sha256"],
        "motion_sha256": digest(args.motion),
        "baseline_sha256": digest(args.baseline),
        "variant_code_sha256": digest(ROOT / "prototype/scripts/probe_right_entry_235_225.py"),
        "runner_sha256": digest(Path(__file__)),
        "intervals": intervals,
        "limitations": ["This rule was selected after reviewing exposed 2024 source clips.",
                        "New prefixes require source review and independent event validation."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps([{"interval": i["interval_s"], "baseline": len(i["baseline_ids"]),
                       "variant": len(i["entry_review_proposals"]),
                       "new_ids": i["new_ids"], "lost": i["baseline_ids_lost"]}
                      for i in intervals]))


if __name__ == "__main__":
    main()
