"""Join pre-event caps and image deltas to the post-cap candidate sequence."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from attach_split_partial_cap_deltas import attach_deltas


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("partial_sequence", "pre", "delta", "output"):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    partial_sequence = json.loads(args.partial_sequence.read_text())
    pre = json.loads(args.pre.read_text())
    delta = json.loads(args.delta.read_text())
    provenance = partial_sequence["partial_cap_handoff_provenance"]
    original_sequence_hash = provenance["candidate_sequence_sha256"]
    if (pre["candidate_sequence_sha256"] != original_sequence_hash
            or delta["input_sha256"]["candidate_sequence"] != original_sequence_hash
            or delta["input_sha256"]["pre_cap_scan"] != digest(args.pre)
            or delta["input_sha256"]["post_cap_scan"] != provenance["partial_cap_scan_sha256"]):
        parser.error("Partial-cap provenance differs")
    result = attach_deltas(partial_sequence, pre, delta)
    result["partial_cap_transition_handoff_provenance"] = {
        "post_cap_partial_sequence_sha256": digest(args.partial_sequence),
        "pre_cap_scan_sha256": digest(args.pre),
        "image_delta_sha256": digest(args.delta),
        "model_code_sha256": digest(ROOT / "prototype/attach_split_partial_cap_deltas.py"),
        "runner_sha256": digest(Path(__file__)),
    }
    result["limitations"].append(
        "Before/after changes are cap visibility differences, not verified stone movements or scoring states.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"candidate_rows": result["sequence_row_count"],
                      "comparison_statuses": result["partial_cap_image_transition_status_counts"]}))


if __name__ == "__main__":
    main()
