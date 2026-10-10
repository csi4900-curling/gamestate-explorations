"""Apply fixed observed-onset cue to a separately source-reviewed right probe."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from right_motion_onset import observed_quiet_to_motion


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("probe", "source-review", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    probe, review = (json.loads(path.read_text()) for path in
                     (args.probe, args.source_review))
    if (review["source_sha256"] != probe["source_sha256"] or
            review["probe_sha256"] != digest(args.probe)):
        raise ValueError("Probe and source review differ")
    classes = {row["raw_track_id"]: row["source_prefix_class"]
               for row in review["rows"]}
    tracks = {row["raw_track_id"]: row for row in
              probe["directional_review_proposals"]}
    if (len(classes) != len(review["rows"]) or len(tracks) != len(
            probe["directional_review_proposals"]) or set(classes) != set(tracks)):
        raise ValueError("Source review must cover every distinct proposal")
    rows = []
    for raw_id, track in sorted(tracks.items()):
        onset = observed_quiet_to_motion(track["observed_prefix_points"],
                                         track["direction"])
        rows.append({"raw_track_id": raw_id,
                     "source_prefix_class": classes[raw_id],
                     "direction": track["direction"],
                     "passage_time_s": track["passage"]["time_s"],
                     "observed_motion_onset": onset,
                     "physical_throw_verified": False})
    counts = Counter((row["source_prefix_class"], row[
        "observed_motion_onset"]["status"]) for row in rows)
    output = {
        "status": "cross_recording_onset_diagnostic_not_throw_accuracy",
        "source_sha256": probe["source_sha256"],
        "source_interval_s": probe["source_interval_s"],
        "input_sha256": {"probe": digest(args.probe),
                         "source_review": digest(args.source_review)},
        "onset_code_sha256": digest(ROOT / "prototype/right_motion_onset.py"),
        "runner_sha256": digest(Path(__file__)),
        "fixed_parameters": {"quiet_rate_px_s": 3, "strong_rate_px_s": 12,
                             "quiet_steps": 3, "strong_steps": 2,
                             "max_sample_gap_s": 1.5,
                             "max_quiet_to_strong_s": 5},
        "proposal_count": len(rows),
        "counts_by_source_class_and_onset_status": {
            cls: {status: count for (label, status), count in sorted(counts.items())
                  if label == cls}
            for cls in sorted(set(classes.values()))},
        "rows": rows,
        "limitations": [
            "The onset thresholds were chosen after reviewing Latvia end-six, and USA was exposed during earlier tracker development.",
            "The source classes are same-agent sampled-frame judgments, not independent physical throw labels.",
            "Insufficient prefix duration is an abstention, not a missed physical throw.",
            "People can also show a quiet-to-motion transition.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"proposals": len(rows),
                      "counts": output["counts_by_source_class_and_onset_status"]}))


if __name__ == "__main__":
    main()
