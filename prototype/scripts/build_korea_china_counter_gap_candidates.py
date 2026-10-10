"""Audit visual-only proposals within the independent 96-shot order."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.counter_gap_candidates import audit_counter_gaps  # noqa: E402

BASE = ROOT / "validation/throw-event-benchmark/paralympics-2022-korea-china"
LEDGER = (
    ROOT
    / "validation/curlobserver-learned-probe/korea-china-full-first-transfer/candidate-event-ledger.json"
)
SLOTS = (
    ROOT / "validation/official-shot-sequence/korea-china-official-counter-slot-handoff-first.json"
)
COLOUR = BASE / "VISUAL-ONLY-COLOUR-HANDOFF.json"
OUTPUT = BASE / "COUNTER-GAP-VISUAL-CANDIDATES.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    ledger = json.loads(LEDGER.read_text())
    slots = json.loads(SLOTS.read_text())
    colour = json.loads(COLOUR.read_text())
    if (
        len({ledger["source_sha256"], slots["source_video_sha256"], colour["source_video_sha256"]})
        != 1
        or colour["candidate_ledger_sha256"] != digest(LEDGER)
        or slots["input_sha256"]["candidate_ledger"] != digest(LEDGER)
    ):
        raise ValueError("Input source or candidate ledger differs")
    groups = audit_counter_gaps(slots["slots"], ledger["events"], colour["rows"])
    result = {
        "status": "postscore_ordinal_candidate_gap_audit_not_physical_throw_validation",
        "source_video_sha256": ledger["source_sha256"],
        "input_sha256": {
            "candidate_ledger": digest(LEDGER),
            "official_counter_slots": digest(SLOTS),
            "visual_colour_handoff": digest(COLOUR),
        },
        "audit_code_sha256": digest(ROOT / "prototype/counter_gap_candidates.py"),
        "runner_sha256": digest(Path(__file__)),
        "group_count": len(groups),
        "status_counts": dict(Counter(group["status"] for group in groups)),
        "missing_slot_count": sum(len(group["missing_official_slots"]) for group in groups),
        "visual_only_candidate_count": sum(
            len(group["visual_only_candidates"]) for group in groups
        ),
        "groups": groups,
        "limitations": [
            "Candidate times are broad release-window starts, not physical release times.",
            "Counter anchors are delayed broadcast proxies, not independently timestamped deliveries.",
            "A unique proposal between anchors is only an ordinal hypothesis; no stone identity is verified.",
            "Official shot colours and diagrams do not provide video timestamps or end-to-end event F1.",
        ],
    }
    payload = json.dumps(result, indent=2) + "\n"
    if OUTPUT.exists():
        if OUTPUT.read_text() != payload:
            raise SystemExit("Existing gap audit differs from inputs or code")
        print(f"Verified {OUTPUT}")
    else:
        OUTPUT.write_text(payload)
        print(f"Wrote {OUTPUT}")
    print(result["status_counts"])


if __name__ == "__main__":
    main()
