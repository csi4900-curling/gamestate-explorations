"""Audit chronology tie-breaks and their counterexamples on four full matches."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from counter_chronology_tiebreak import audit_counter_chronology

BASE = ROOT / "validation/curlobserver-learned-probe"
INPUTS = {
    "PREL000101": (
        BASE / "swiss-full-transfer/counter-cap.json",
        BASE / "swiss-full-transfer/shot-origin.json",
    ),
    "PREL000102": (
        BASE / "china-full-transfer/counter-shot-alignment-replay-cap.json",
        BASE / "china-full-transfer/unlabelled-shot-origin-inference.json",
    ),
    "PREL000103": (
        BASE / "slovakia-full-transfer/counter-cap.json",
        BASE / "slovakia-full-transfer/shot-origin.json",
    ),
    "CAN-NOR-2022": (
        BASE / "canada-norway-full-transfer/counter-cap.json",
        BASE / "canada-norway-full-transfer/shot-origin.json",
    ),
}
OUTPUT = (
    ROOT / "validation/official-shot-sequence/pwg2022-counter-chronology-tiebreak-development.json"
)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def build():
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    games = []
    for code, (alignment_path, origin_path) in INPUTS.items():
        alignment, origins = (
            json.loads(path.read_text()) for path in (alignment_path, origin_path)
        )
        source = origins["source_sha256"]
        if source == reserved["source_sha256"] or alignment["source_sha256"] != source:
            raise ValueError(f"Source mismatch or reserved source selected: {code}")
        audit = audit_counter_chronology(alignment["rows"])
        games.append(
            {
                "recording_code": code,
                "source_sha256": source,
                "input_sha256": {
                    "counter_alignment": digest(alignment_path),
                    "shot_origins": digest(origin_path),
                },
                "counter_update_count": len(alignment["rows"]),
                "ambiguous_counter_count": len(audit["ambiguous_rows"]),
                "unique_chronological_choice_count": sum(
                    row["chosen_shot_id"] is not None for row in audit["ambiguous_rows"]
                ),
                "existing_link_temporal_conflict_count": len(
                    audit["existing_link_temporal_conflicts"]
                ),
                **audit,
            }
        )
    return {
        "status": "development_counter_chronology_diagnostic_no_event_mutation",
        "rule": "For a multi-option unassociated counter, keep options with origin probability >=0.2 and shot end >= the previous observed counter update. Choose only if exactly one survives.",
        "code_sha256": digest(ROOT / "prototype/counter_chronology_tiebreak.py"),
        "runner_sha256": digest(Path(__file__)),
        "games": games,
        "limitations": [
            "The rule was proposed after inspecting Norway B69; all four recordings were already exposed for development.",
            "A broadcast counter can update after the next physical delivery; six existing associated shots violate the proposed ordering condition.",
            "A unique chronological option is not verified physical stone identity or event ground truth.",
            "No candidate, counter link or full-match throw F1 is changed by this audit.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists():
        if OUTPUT.read_text() != payload:
            raise SystemExit("Existing chronology audit differs from inputs or code")
        print(f"Verified {OUTPUT}")
    else:
        OUTPUT.write_text(payload)
        print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
