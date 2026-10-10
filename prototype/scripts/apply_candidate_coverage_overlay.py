"""Apply a source-reviewed routed-coverage overlay to candidate evidence."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from rebase_candidate_coverage import rebase_candidate_coverage


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("sequence", "coverage", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    sequence, overlay = [json.loads(path.read_text()) for path in (args.sequence, args.coverage)]
    frozen_hash = overlay["coverage_overlay_provenance"]["frozen_timeline_sha256"]
    if sequence["input_sha256"]["timeline"] != frozen_hash:
        parser.error("Candidate sequence and coverage overlay have different frozen timelines")
    result = rebase_candidate_coverage(sequence, overlay)
    result["coverage_rebase_provenance"] = {
        "candidate_sequence_sha256": digest(args.sequence),
        "coverage_overlay_sha256": digest(args.coverage),
        "model_code_sha256": digest(ROOT / "prototype/rebase_candidate_coverage.py"),
        "runner_sha256": digest(Path(__file__)),
    }
    result["limitations"].append(
        "Terminal credits are excluded from routed support; no event, board or spin claim changed."
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "rows": len(result["rows"]),
                "supported_runs": result["supported_runs"],
                "coverage_gaps_s": result["coverage_gaps_s"],
            }
        )
    )


if __name__ == "__main__":
    main()
