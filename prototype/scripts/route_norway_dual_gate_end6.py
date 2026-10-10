"""First source-only end-6 orientation and colour decisions from frozen gates."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from dual_departure_gate import route_gate_sides

BASE = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1"
VISUAL = BASE / "norway-end6-dual-gate-first.json"
FROZEN = BASE / "norway-end4-end5-dual-gate-development.json"
OUTPUT = BASE / "norway-end6-dual-gate-events-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first end-6 routed decisions")
    visual, frozen = (json.loads(path.read_text()) for path in (VISUAL, FROZEN))
    if visual["source_sha256"] != frozen["source_sha256"]:
        raise ValueError("Source mismatch")
    if frozen["router_code_sha256"] != digest(ROOT / "prototype/dual_departure_gate.py") or frozen[
        "colour_code_sha256"
    ] != digest(ROOT / "prototype/departure_gate_decision.py"):
        raise ValueError("Routing or colour decision changed after development")
    decisions = route_gate_sides(visual["rows"])
    result = {
        "status": "source_only_first_end6_mirrored_gate_event_decisions",
        "source_sha256": visual["source_sha256"],
        "visual_scan_sha256": digest(VISUAL),
        "frozen_router_sha256": digest(FROZEN),
        "router_code_sha256": digest(ROOT / "prototype/dual_departure_gate.py"),
        "runner_sha256": digest(Path(__file__)),
        "end": 6,
        "origin_positive_count": len(decisions),
        "colour_resolved_count": sum(row["colour"] is not None for row in decisions),
        "decisions": decisions,
        "limitations": [
            "Router and gate geometry were selected on exposed ends four and five of the same recording.",
            "Early-gate anchors are visual line observations, not physical release timestamps.",
            "No counter, official sequence, or board state enters the routing decisions.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    for row in decisions:
        print(row["shot_id"], row["side"], row["colour"], row["side_route"])


if __name__ == "__main__":
    main()
