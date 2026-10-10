"""Freeze Norway counter gaps with adjacent source-video candidate evidence."""

from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.counter_gap_inventory import inventory_gaps


SLOTS = ROOT / "validation/official-shot-sequence/norway-full-match-official-counter-slot-scaffold-first.json"
EVENTS = ROOT / "validation/curlobserver-learned-probe/canada-norway-full-transfer/fused-linked.json"
DISPLAY = ROOT / "validation/official-shot-sequence/norway-counterless-candidate-end-display-v2.json"
OUTPUT = ROOT / "validation/official-shot-sequence/norway-counter-gap-inventory-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("First counter gap inventory already exists")
    slots = json.loads(SLOTS.read_text())
    events = json.loads(EVENTS.read_text())
    display = json.loads(DISPLAY.read_text())
    if events["source_sha256"] != display["source_video_sha256"]:
        raise SystemExit("Candidate/display video source hash conflict")
    if slots["input_sha256"]["candidate_ledger"] != digest(EVENTS):
        raise SystemExit("Scaffold candidate ledger hash conflict")
    rows = inventory_gaps(slots["slots"], events["events"], display["rows"])
    output = {
        "status": "chronological_counter_gap_inventory_not_verified_throw_identity",
        "input_sha256": {"slot_scaffold": digest(SLOTS), "candidate_ledger": digest(EVENTS),
                         "display_audit": digest(DISPLAY)},
        "inventory_code_sha256": digest(ROOT / "prototype/counter_gap_inventory.py"),
        "runner_sha256": digest(Path(__file__)),
        "gap_count": len(rows),
        "gaps_with_missing_counter_slots": sum(bool(row["missing_slots"]) for row in rows),
        "unique_order_colour_display_proposal_count": sum(
            row["unique_order_colour_display_proposal"] is not None for row in rows),
        "gaps": rows,
        "limitations": [
            "Only intervals between video-linked counter anchors are inventoried; terminal ends are not resolved.",
            "Chronology uses provisional candidate window starts, not observed physical release time.",
            "A unique order/colour/display proposal is still not a verified physical throw or stone identity.",
            "The on-screen end can lag physical play at transitions; unknown labels do not exclude candidates.",
            "Counterless candidates may be duplicate views or false positives, and missing counters may hide true throws.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print({key: output[key] for key in ("gap_count", "gaps_with_missing_counter_slots",
                                          "unique_order_colour_display_proposal_count")})


if __name__ == "__main__":
    main()
