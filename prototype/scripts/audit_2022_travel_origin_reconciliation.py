"""Preserve adjacency conflicts between travel cues and fused visual events."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from travel_origin_reconciliation import classify_travel_predecessors

BASE = ROOT / "validation/official-shot-sequence"
TRAVEL = BASE / "pwg2022-cap-fusion-travel-rescue-development.json"
INPUTS = {
    "PREL000101": (ROOT / "validation/curlobserver-learned-probe/swiss-full-transfer/shot-origin.json",
                   ROOT / "validation/curlobserver-learned-probe/swiss-full-transfer/fused-cap.json"),
    "PREL000102": (ROOT / "validation/curlobserver-learned-probe/china-full-transfer/unlabelled-shot-origin-inference.json",
                   ROOT / "validation/curlobserver-learned-probe/china-full-transfer/fused-shot-candidates-replay-cap.json"),
    "PREL000103": (ROOT / "validation/curlobserver-learned-probe/slovakia-full-transfer/shot-origin.json",
                   ROOT / "validation/curlobserver-learned-probe/slovakia-full-transfer/fused-cap.json"),
}
OUTPUT = BASE / "pwg2022-travel-origin-reconciliation-development.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def build():
    travel = json.loads(TRAVEL.read_text())
    games = []
    for source in travel["games"]:
        code = source["official_game_code"]
        origin_path, fused_path = INPUTS[code]
        if (source["input_sha256"]["origins"] != digest(origin_path) or
                source["input_sha256"]["cap_fusion"] != digest(fused_path)):
            raise ValueError(f"Travel and fused input hashes differ: {code}")
        origins, fused = (json.loads(path.read_text()) for path in
                          (origin_path, fused_path))
        if origins["source_sha256"] != source["source_sha256"] or (
                fused["source_sha256"] != source["source_sha256"]):
            raise ValueError(f"Recording source differs: {code}")
        rows = classify_travel_predecessors(origins["rows"], fused["events"],
                                             source["rows"])
        counts = dict(sorted(Counter(row["relation_status"] for row in rows).items()))
        if len(rows) != source["travel_proposal_count"]:
            raise ValueError(f"Travel proposal count changed: {code}")
        games.append({
            "official_game_code": code,
            "source_sha256": source["source_sha256"],
            "input_sha256": {"origins": digest(origin_path),
                             "cap_fusion": digest(fused_path)},
            "travel_proposal_count": len(rows),
            "relation_counts": counts,
            "possible_same_throw_pair_count": sum(
                row["possible_same_physical_throw"] for row in rows),
            "rows": rows,
        })
    return {
        "status": "source_scoped_development_adjacency_hypotheses_no_event_merges",
        "travel_audit_sha256": digest(TRAVEL),
        "classification_code_sha256": digest(ROOT / "prototype/travel_origin_reconciliation.py"),
        "runner_sha256": digest(Path(__file__)),
        "games": games,
        "limitations": [
            "Adjacent camera shots may contain different physical throws; adjacency is a review hypothesis only.",
            "Colour agreement does not prove identity and disagreement does not prove two throws.",
            "No existing event is suppressed and no travel proposal is promoted by this audit.",
            "This is exposed-source development evidence, not independent precision, recall or F1.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists():
        if OUTPUT.read_text() != payload:
            raise SystemExit("Existing reconciliation differs from current inputs or code")
        print(f"Verified {OUTPUT}")
    else:
        OUTPUT.write_text(payload)
        print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
