"""Freeze a source-only duplicate-evidence proposal on three full ledgers."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.candidate_duplicate_evidence import (
    contained_visual_duplicates, fuse_candidate_events,
)

ALIGNMENT = ROOT / "validation/official-shot-sequence/pwg2022-official-counter-alignment.json"
SEQUENCE = ROOT / "validation/official-shot-sequence/pwg2022-official-candidate-sequence-postcut-audit.json"
OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-candidate-duplicate-fusion.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first full-ledger duplicate audit")
    alignment = json.loads(ALIGNMENT.read_text())
    sequence = json.loads(SEQUENCE.read_text())
    audits = {game["official_game_code"]: game for game in sequence["games"]}
    games = []
    for game in alignment["games"]:
        code = game["official_game_code"]
        path = ROOT / game["candidate_ledger_path"]
        if digest(path) != game["candidate_ledger_sha256"]:
            raise ValueError(f"Candidate ledger hash mismatch: {code}")
        events = json.loads(path.read_text())["events"]
        duplicates = contained_visual_duplicates(events)
        fused = fuse_candidate_events(events, duplicates)
        statuses = {row["candidate_id"]: row["status"]
                    for end in audits[code]["ends"] for row in end["candidate_rows"]}
        games.append({
            "official_game_code": code,
            "candidate_ledger_path": game["candidate_ledger_path"],
            "candidate_ledger_sha256": digest(path),
            "raw_candidate_count": len(events),
            "fused_event_count": len(fused),
            "duplicates": [{"candidate_id": identifier, **decision,
                            "development_sequence_status": statuses[identifier]}
                           for identifier, decision in sorted(duplicates.items())],
            "fused_events": fused,
        })
    output = {
        "status": "source_only_duplicate_evidence_fusion_proposal_not_event_f1",
        "alignment_sha256": digest(ALIGNMENT),
        "development_sequence_audit_sha256": digest(SEQUENCE),
        "fusion_code_sha256": digest(ROOT / "prototype/candidate_duplicate_evidence.py"),
        "runner_sha256": digest(Path(__file__)),
        "rule": "A visual-only candidate is grouped into exactly one counter-backed candidate when its entire release window lies within that counter-backed release window (0.25-second boundary tolerance) and colours do not conflict. Ambiguous cases abstain. All original IDs remain in fused-event provenance.",
        "raw_candidate_count": sum(row["raw_candidate_count"] for row in games),
        "fused_event_count": sum(row["fused_event_count"] for row in games),
        "duplicate_evidence_count": sum(len(row["duplicates"]) for row in games),
        "games": games,
        "limitations": [
            "Containment is evidence of overlap, not independent proof that the visual candidate was false; this is a proposed event representation.",
            "Counter-backed release windows can be broad or mislocalized, so a future transfer must verify that no real adjacent throw is absorbed.",
            "The official sequence status is added only after source-only grouping and is edit-cost dependent; it is not a true/false label.",
            "No complete-recording independent throw timestamps or precision/recall are available from this audit.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print({key: output[key] for key in
           ("raw_candidate_count", "fused_event_count", "duplicate_evidence_count")})


if __name__ == "__main__":
    main()
