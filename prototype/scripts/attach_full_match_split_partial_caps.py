"""Join a source-video partial-cap scan to its exact candidate sequence."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from attach_split_partial_caps import attach_partial_caps


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("sequence", "scan", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    sequence = json.loads(args.sequence.read_text())
    scan = json.loads(args.scan.read_text())
    if scan["candidate_sequence_sha256"] != digest(args.sequence):
        parser.error("Partial-cap scan sequence provenance differs")
    result = attach_partial_caps(sequence, scan)
    result["partial_cap_handoff_provenance"] = {
        "candidate_sequence_sha256": digest(args.sequence),
        "partial_cap_scan_sha256": digest(args.scan),
        "model_code_sha256": digest(ROOT / "prototype/attach_split_partial_caps.py"),
        "runner_sha256": digest(Path(__file__)),
    }
    result["limitations"].extend(
        [
            "Post-candidate cap samples are partial right-camera pixels, not a complete settled board.",
            "An intervening missed delivery or player handling can contaminate the sampled window.",
        ]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "candidate_rows": result["sequence_row_count"],
                "partial_caps": result["stable_cap_proposal_count"],
                "statuses": result["partial_cap_observation_status_counts"],
            }
        )
    )


if __name__ == "__main__":
    main()
