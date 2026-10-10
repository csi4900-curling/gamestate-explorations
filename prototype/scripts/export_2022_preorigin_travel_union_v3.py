"""Append the China B02 counter-linked receiving-travel rescue to the v2 union."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.preorigin_travel_union import append_preorigin_travel_rescues

BASE = ROOT / "validation/official-shot-sequence"
UNION = BASE / "pwg2022-provisional-event-evidence-union-v2-source-rescues-development.json"
PROPOSALS = BASE / "pwg2022-preorigin-travel-rescue-proposals-development.json"
OUTPUT = BASE / "pwg2022-provisional-event-evidence-union-v3-preorigin-travel-development.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def build():
    union = json.loads(UNION.read_text())
    proposal_file = json.loads(PROPOSALS.read_text())
    proposals = proposal_file["proposals"]
    if len(proposals) != 1 or proposal_file["proposal_count"] != 1:
        raise ValueError("Expected one preorigin travel proposal")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    games = []
    for game in union["games"]:
        code = game["official_game_code"]
        source = game["source_sha256"]
        if source == reserved["source_sha256"]:
            raise ValueError("Reserved source cannot enter development union")
        local = [row for row in proposals if row["recording_code"] == code]
        if any(row["source_sha256"] != source for row in local):
            raise ValueError("Proposal source mismatch")
        events = append_preorigin_travel_rescues(game["events"], local)
        events.sort(key=lambda event: (
            min(int(shot[1:]) for shot in event["source_shot_ids"]),
            event["event_id"]))
        consumed = {row["counter_id"] for row in local}
        unassigned = sorted(set(game["remaining_unassigned_counter_ids"]) - consumed)
        if not consumed <= set(game["remaining_unassigned_counter_ids"]):
            raise ValueError("Rescue counter was not unassigned in v2")
        games.append({**{key: value for key, value in game.items()
                         if key not in ("events", "provisional_event_count",
                                        "counter_linked_event_count",
                                        "remaining_unassigned_counter_count",
                                        "remaining_unassigned_counter_ids",
                                        "candidate_class_counts")},
                      "provisional_event_count": len(events),
                      "counter_linked_event_count": game[
                          "counter_linked_event_count"] + len(local),
                      "remaining_unassigned_counter_count": len(unassigned),
                      "remaining_unassigned_counter_ids": unassigned,
                      "candidate_class_counts": dict(sorted(Counter(
                          event["candidate_class"] for event in events).items())),
                      "events": events})
    return {"status": "development_provisional_event_union_v3_preorigin_travel_not_physical_f1",
            "input_sha256": {"v2_union": digest(UNION),
                             "preorigin_travel_proposal": digest(PROPOSALS),
                             "merge_code": digest(ROOT / "prototype/preorigin_travel_union.py"),
                             "runner": digest(Path(__file__))},
            "total_provisional_event_count": sum(g["provisional_event_count"]
                                                 for g in games),
            "preorigin_travel_rescue_count": len(proposals),
            "games": games,
            "limitations": [
                "The China B02 row is an additive provisional candidate; the v2 358-event baseline remains frozen separately.",
                "The receiving-view cap passage is travel evidence, not a measured physical release time.",
                "Origin-view and receiving-view physical stone identity is not verified.",
                "No independent physical event F1, complete settled board, or simulation-ready trajectory is established.",
            ]}


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists() and OUTPUT.read_text() != payload:
        raise SystemExit("Existing v3 union differs from hashed inputs")
    if not OUTPUT.exists():
        OUTPUT.write_text(payload)
    print(f"Verified {OUTPUT}")


if __name__ == "__main__":
    main()
