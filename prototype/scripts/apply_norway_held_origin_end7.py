"""First source-only end-7 transfer of the frozen held-cap arbitration."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from held_origin_decision import combine_with_gate

BASE = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1"
GATE = BASE / "norway-end7-dual-gate-events-first.json"
HELD = BASE / "norway-end7-held-origin-first.json"
FROZEN = BASE / "norway-end6-held-origin-events-development.json"
OUTPUT = BASE / "norway-end7-held-origin-events-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first end-7 held-cap arbitration")
    gate, held = (json.loads(path.read_text()) for path in (GATE, HELD))
    frozen = json.loads(FROZEN.read_text())
    if gate["source_sha256"] != held["source_sha256"]:
        raise ValueError("Source mismatch")
    if frozen["decision_code_sha256"] != digest(ROOT / "prototype/held_origin_decision.py"):
        raise ValueError("Held-cap arbitration changed after end six")
    by_id = {row["shot_id"]: row for row in held["rows"]}
    if set(by_id) != {row["shot_id"] for row in gate["decisions"]}:
        raise ValueError("Held and gate shot sets differ")
    decisions = []
    for row in gate["decisions"]:
        cue = combine_with_gate(row["colour"], by_id[row["shot_id"]]["evidence"])
        decisions.append({"shot_id": row["shot_id"],
                          "interval_s": row["interval_s"],
                          "side": row["side"],
                          "gate_colour": row["colour"],
                          "colour": cue["colour"],
                          "route": cue["route"],
                          "held_override": cue["held_override"]})
    result = {
        "status": "source_only_first_end7_held_cap_arbitration_transfer",
        "source_sha256": gate["source_sha256"],
        "gate_first_sha256": digest(GATE),
        "held_diagnostic_sha256": digest(HELD),
        "frozen_end6_arbitration_sha256": digest(FROZEN),
        "decision_code_sha256": digest(ROOT / "prototype/held_origin_decision.py"),
        "runner_sha256": digest(Path(__file__)),
        "end": 7,
        "decisions": decisions,
        "candidate_count": sum(row["colour"] is not None for row in decisions),
        "override_count": sum(row["route"] == "held_cap_overrode_gate" for row in decisions),
        "limitations": [
            "Central corridor, held/motion thresholds and arbitration were selected on exposed end six, then frozen for this transfer.",
            "A held cap is not a measured release or cross-cut identity.",
            "No official shot or counter colour enters the arbitration function.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print({"candidates": result["candidate_count"],
           "overrides": result["override_count"]})


if __name__ == "__main__":
    main()
