"""Replay the existing travel fallback on three cap-fusion event ledgers."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from counter_travel_fallback import travel_only_candidates

BASE = ROOT / "validation/curlobserver-learned-probe"
HANDOFF = ROOT / "validation/official-shot-sequence"
INPUTS = {
    "PREL000101": ("swiss-full-transfer", "shot-origin.json", "cap-motion.json",
                   "selected-learned-motion.json", "counter-cap.json", "fused-cap.json"),
    "PREL000102": ("china-full-transfer", "unlabelled-shot-origin-inference.json",
                   "sequential-shot-cap-motion.json", "selected-shot-learned-motion.json",
                   "counter-shot-alignment-replay-cap.json",
                   "fused-shot-candidates-replay-cap.json"),
    "PREL000103": ("slovakia-full-transfer", "shot-origin.json", "cap-motion.json",
                   "selected-learned-motion.json", "counter-cap.json", "fused-cap.json"),
}
HELD = HANDOFF / "pwg2022-held-origin-counter-rescue-development.json"
OUTPUT = HANDOFF / "pwg2022-cap-fusion-travel-rescue-development.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def build():
    held = json.loads(HELD.read_text())
    held_by_game = {row["official_game_code"]: row for row in held["games"]}
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    games = []
    for code, names in INPUTS.items():
        folder, *filenames = names
        paths = [BASE / folder / name for name in filenames]
        origin, cap, learned, align, fused = (json.loads(path.read_text()) for path in paths)
        source = fused["source_sha256"]
        if source == reserved["source_sha256"] or any(
                row["source_sha256"] != source
                for row in (origin, cap, learned, align)):
            raise ValueError(f"Source mismatch or reserved source selected: {code}")
        if (fused["counter_alignment_sha256"] != digest(paths[3]) or
                fused["origins_sha256"] != digest(paths[0])):
            raise ValueError(f"Fused dependency mismatch: {code}")
        if len(origin["rows"]) != len(cap["shots"]) or len(
                origin["rows"]) != len(learned["shots"]):
            raise ValueError(f"Incomplete motion rows: {code}")
        rows = travel_only_candidates(align["rows"], origin["rows"], cap["shots"],
                                      learned["shots"], fused["events"])
        if {row["counter_id"] for row in rows} != {
                row["counter_id"] for row in fused["unassociated_counter_events"]}:
            raise ValueError(f"Counter gap set changed: {code}")
        proposals = [row for row in rows
                     if row["status"] == "unlocalized_travel_candidate"]
        for proposal in proposals:
            shot_id = proposal["travel_shot_id"]
            selected = next(row for row in learned["shots"] if row["shot_id"] == shot_id)
            if not selected["scanned"]:
                raise ValueError(f"Travel proposal uses unscanned learned shot: {code} {shot_id}")
        held_ids = {row["counter_id"] for row in held_by_game[code]["proposals"]}
        travel_ids = {row["counter_id"] for row in proposals}
        games.append({
            "official_game_code": code,
            "source_sha256": source,
            "input_sha256": dict(zip(("origins", "cap_motion", "learned_motion",
                                       "counter_alignment", "cap_fusion"),
                                      map(digest, paths), strict=True)),
            "baseline_event_count": fused["candidate_count"],
            "unassociated_counter_count": len(rows),
            "travel_proposal_count": len(proposals),
            "counter_gaps_remaining_after_travel": len(rows) - len(proposals),
            "held_origin_proposal_count": len(held_ids),
            "held_and_travel_counter_overlap": sorted(held_ids & travel_ids),
            "unique_counter_proposals_across_lanes": len(held_ids | travel_ids),
            "rows": rows,
        })
    return {
        "status": "postscore_crossrecording_travel_proposal_coverage_not_event_f1",
        "held_proposals_sha256": digest(HELD),
        "travel_code_sha256": digest(ROOT / "prototype/counter_travel_fallback.py"),
        "runner_sha256": digest(Path(__file__)),
        "games": games,
        "limitations": [
            "The cap and learned tracks are correlated image evidence, not independent physical stone identity.",
            "Learned motion was scanned on selected shots using prior counter and fusion evidence; unscanned shots are not negatives.",
            "A delayed counter can change before the receiving-view track appears, so release windows remain broad.",
            "This source-exposed replay is a candidate coverage audit, not physical precision, recall or F1.",
            "Travel and held-origin lanes may describe the same physical throw; counter overlap is reported and must be deduplicated.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists():
        if OUTPUT.read_text() != payload:
            raise SystemExit("Existing travel audit differs from current inputs or code")
        print(f"Verified {OUTPUT}")
    else:
        OUTPUT.write_text(payload)
        print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
