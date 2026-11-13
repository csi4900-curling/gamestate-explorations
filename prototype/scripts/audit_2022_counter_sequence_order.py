"""Reproducible source-scoped counter/shot order diagnostic on four matches."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from counter_sequence_order import audit_counter_sequence_order

BASE = ROOT / "validation/curlobserver-learned-probe"
INPUTS = {
    "PREL000101": BASE / "swiss-full-transfer/counter-cap.json",
    "PREL000102": BASE / "china-full-transfer/counter-shot-alignment-replay-cap.json",
    "PREL000103": BASE / "slovakia-full-transfer/counter-cap.json",
    "CAN-NOR-2022": BASE / "canada-norway-full-transfer/counter-cap.json",
}
OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-counter-sequence-order-development.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def build():
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    games = []
    for code, path in INPUTS.items():
        source = json.loads(path.read_text())
        if source["source_sha256"] == reserved["source_sha256"]:
            raise ValueError("Reserved recording cannot enter development audit")
        result = audit_counter_sequence_order(source["rows"])
        games.append(
            {
                "recording_code": code,
                "source_sha256": source["source_sha256"],
                "input_sha256": digest(path),
                "counter_count": len(source["rows"]),
                "anchor_reversal_count": len(result["anchor_reversals"]),
                "multi_option_counter_count": len(result["multi_option_counter_proposals"]),
                "unique_order_proposal_count": sum(
                    row["proposed_shot_id"] is not None
                    for row in result["multi_option_counter_proposals"]
                ),
                **result,
            }
        )
    return {
        "status": "development_order_diagnostic_no_event_mutation",
        "rule": "Keep origin probability >=0.2 options whose camera-shot number is strictly between nearest already linked counters' camera-shot numbers; propose only a unique survivor.",
        "code_sha256": digest(ROOT / "prototype/counter_sequence_order.py"),
        "runner_sha256": digest(Path(__file__)),
        "games": games,
        "limitations": [
            "All four recordings are exposed development sources; no independent event labels were used.",
            "Existing counter links are provisional and can be reversed or wrong.",
            "Shot order alone does not prove a release, physical stone identity, or settled board transition.",
            "No event count, event ledger, or measured physical throw F1 changes.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists():
        if OUTPUT.read_text() != payload:
            raise SystemExit("Existing order audit differs from inputs or code")
        print(f"Verified {OUTPUT}")
    else:
        OUTPUT.write_text(payload)
        print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
