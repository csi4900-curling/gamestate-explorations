"""Build a full-match candidate handoff with conditional receiving-view caps."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from attach_routed_partial_caps import attach_routed_partial_caps


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("sequence", "routes", "left-scan", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    sequence = json.loads(args.sequence.read_text())
    routes = json.loads(args.routes.read_text())
    left_scan = json.loads(args.left_scan.read_text())
    if (routes["sequence_sha256"] != digest(args.sequence) or
            left_scan["sequence_sha256"] != digest(args.sequence) or
            left_scan["routes_sha256"] != digest(args.routes)):
        raise ValueError("Route or left-scan lineage differs from sequence")
    result = attach_routed_partial_caps(sequence, routes, left_scan)
    result["conditional_board_view_provenance"] = {
        "sequence_sha256": digest(args.sequence),
        "routes_sha256": digest(args.routes),
        "left_scan_sha256": digest(args.left_scan),
        "model_code_sha256": digest(ROOT / "prototype/attach_routed_partial_caps.py"),
        "runner_sha256": digest(Path(__file__)),
    }
    result["limitations"].extend([
        "Receiving view is conditional on unverified cross-camera event links.",
        "Stable image caps can include people or equipment; no physical board is inferred.",
        "The left scan was developed after source review of Estonia S38.",
    ])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"source": result["source_id"],
                      "rows": len(result["rows"]),
                      "view_counts": result["receiving_view_counts"],
                      "statuses": result["receiving_view_status_counts"]}))


if __name__ == "__main__":
    main()
