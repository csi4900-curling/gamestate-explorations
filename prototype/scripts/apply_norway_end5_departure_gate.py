"""Create first source-only end-5 events with the frozen early-gate rule."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from departure_gate_decision import decide_gate_colour

BASE = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1"
GATE = BASE / "norway-end5-departure-gate-first.json"
FROZEN = BASE / "norway-end4-departure-gate-events-development.json"
OUTPUT = BASE / "norway-end5-departure-gate-events-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first end-5 gate decision")
    gate = json.loads(GATE.read_text())
    frozen = json.loads(FROZEN.read_text())
    if frozen["decision_code_sha256"] != digest(ROOT / "prototype/departure_gate_decision.py"):
        raise ValueError("Decision rule changed after end four")
    decisions = []
    for row in gate["rows"]:
        choice = decide_gate_colour(row)
        decisions.append({"candidate_id": f"{row['shot_id']}-early-gate",
                          "origin_shot_id": row["shot_id"],
                          "release_window_s": row["interval_s"],
                          "early_gate_anchor_s": choice["anchor_s"],
                          "colour": choice["colour"],
                          "evidence_route": choice["route"],
                          "gate_counts": row["gate_counts"],
                          "transits": row["transits"]})
    result = {
        "status": "source_only_first_end5_early_gate_event_decisions",
        "source_sha256": gate["source_sha256"],
        "gate_observations_sha256": digest(GATE),
        "frozen_end4_decisions_sha256": digest(FROZEN),
        "decision_code_sha256": digest(ROOT / "prototype/departure_gate_decision.py"),
        "runner_sha256": digest(Path(__file__)),
        "end": 5,
        "origin_positive_count": len(decisions),
        "colour_resolved_count": sum(row["colour"] is not None for row in decisions),
        "decisions": decisions,
        "limitations": [
            "The gate and colour rule were designed on exposed end four and frozen before this first end-five score.",
            "The anchor is a visual line observation, not a measured release time.",
            "Origin view classification and pixel gate are specific to this broadcast layout.",
            "No official shot order, counter, or board position enters the colour decision.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print({"origin_positives": len(decisions),
           "colours": {colour: sum(row["colour"] == colour for row in decisions)
                       for colour in ("red", "yellow", None)}})


if __name__ == "__main__":
    main()
