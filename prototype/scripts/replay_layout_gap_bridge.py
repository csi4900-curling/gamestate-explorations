"""Replay a fixed short-gap bridge over a saved full-source preflight."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from layout_gap_bridge import bridge_split_gaps


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve the first replay")
    source = json.loads(args.preflight.read_text())
    result = bridge_split_gaps(source)
    result.update({
        "status": "postscore_development_layout_bridge_not_continuous_coverage",
        "upstream_preflight_artifact_sha256": digest(args.preflight),
        "bridge_code_sha256": digest(ROOT / "prototype/layout_gap_bridge.py"),
        "bridge_runner_sha256": digest(Path(__file__)),
        "limitations": source["limitations"] + [
            "Bridged chunks have conditional split geometry, not verified continuous view or throws.",
            "The rule was fitted after inspecting Scotland's exposed full-source gaps.",
        ],
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"promoted": result["bridge_promoted_intervals_s"],
                      "remaining_gaps": result["coverage_gaps_s"]}))


if __name__ == "__main__":
    main()
