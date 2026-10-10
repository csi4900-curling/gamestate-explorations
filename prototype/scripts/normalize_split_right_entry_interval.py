"""Adapt one saved static-left right-entry interval for transfer comparison."""

import argparse
from hashlib import sha256
import json
from pathlib import Path


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion", type=Path, required=True)
    parser.add_argument("--triage", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    motion = json.loads(args.motion.read_text())
    triage = json.loads(args.triage.read_text())
    if (
        len(motion["intervals"]) != 1
        or len(triage["intervals"]) != 1
        or triage["source_sha256"] != motion["source_sha256"]
        or triage["probe_sha256"] != digest(args.motion)
    ):
        parser.error("Expected one matching source/interval pair")
    raw = motion["intervals"][0]
    entries = triage["intervals"][0]
    if (
        raw["interval_s"] != entries["interval_s"]
        or raw["moving_track_count"] != entries["raw_track_count"]
        or len(entries["entry_review_proposals"]) != entries["entry_review_count"]
    ):
        parser.error("Saved motion and triage counts disagree")
    output = {
        "status": "saved_static_left_right_entry_baseline_adapter_not_throw_labels",
        "source_sha256": motion["source_sha256"],
        "source_interval_s": entries["interval_s"],
        "raw_track_count": entries["raw_track_count"],
        "entry_review_proposals": entries["entry_review_proposals"],
        "input_sha256": {"motion": digest(args.motion), "triage": digest(args.triage)},
        "runner_sha256": digest(Path(__file__)),
        "limitations": [
            "This copies candidate metadata; it does not re-detect or verify physical throws.",
            "The 2024 right-entry tier was selected after source inspection.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "interval": output["source_interval_s"],
                "entries": len(output["entry_review_proposals"]),
            }
        )
    )


if __name__ == "__main__":
    main()
