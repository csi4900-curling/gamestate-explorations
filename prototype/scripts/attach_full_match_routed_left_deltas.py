"""Add pre/post left-view image changes to routed full-match candidate state."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from attach_routed_left_cap_deltas import attach_routed_left_cap_deltas


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("sequence", "pre", "delta", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    sequence = json.loads(args.sequence.read_text())
    pre = json.loads(args.pre.read_text())
    delta = json.loads(args.delta.read_text())
    provenance = sequence["conditional_board_view_provenance"]
    if (pre["sequence_sha256"] != provenance["sequence_sha256"] or
            pre["routes_sha256"] != provenance["routes_sha256"] or
            delta["routes_sha256"] != provenance["routes_sha256"] or
            delta["pre_sha256"] != digest(args.pre) or
            delta["post_sha256"] != provenance["left_scan_sha256"]):
        raise ValueError("Pre/delta lineage differs from routed sequence")
    result = attach_routed_left_cap_deltas(sequence, pre, delta)
    result["receiving_view_delta_provenance"] = {
        "routed_sequence_sha256": digest(args.sequence),
        "pre_left_scan_sha256": digest(args.pre),
        "left_delta_sha256": digest(args.delta),
        "model_code_sha256": digest(ROOT / "prototype/attach_routed_left_cap_deltas.py"),
        "runner_sha256": digest(Path(__file__)),
    }
    result["limitations"].extend([
        "Cap changes describe partial camera-local image observations only.",
        "Retained static markings and newly visible coloured objects are not physical stone IDs.",
        "Unobserved shots and occlusion may alter the apparent pre/post delta.",
    ])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"source": result["source_id"],
                      "rows": len(result["rows"]),
                      "left_delta_statuses": result["left_receiving_transition_status_counts"]}))


if __name__ == "__main__":
    main()
