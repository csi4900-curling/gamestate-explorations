"""Combine re-linked visual events with deduplicated travel and held cues."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from provisional_event_union import combine_event_evidence

BASE = ROOT / "validation/official-shot-sequence"
LINKED = BASE / "pwg2022-cap-visual-counter-links-development.json"
TRAVEL = BASE / "pwg2022-cap-fusion-travel-rescue-development.json"
RELATIONS = BASE / "pwg2022-travel-origin-reconciliation-development.json"
HELD = BASE / "pwg2022-held-origin-counter-rescue-development.json"
OUTPUT = BASE / "pwg2022-provisional-event-evidence-union-development.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def build():
    linked, travel, relations, held = (json.loads(path.read_text()) for path in
                                       (LINKED, TRAVEL, RELATIONS, HELD))
    by_code = [{row["official_game_code"]: row for row in data["games"]}
               for data in (linked, travel, relations, held)]
    if not all(set(by_code[0]) == set(index) for index in by_code[1:]):
        raise ValueError("Evidence recordings differ")
    games = []
    for code, link in by_code[0].items():
        motion, relation, origin = (index[code] for index in by_code[1:])
        source = link["source_sha256"]
        if any(row["source_sha256"] != source for row in
               (motion, relation, origin)):
            raise ValueError(f"Source hashes differ: {code}")
        combined = combine_event_evidence(
            link["events"], motion["rows"], relation["rows"], origin["proposals"])
        events = sorted(combined["events"], key=lambda row: (
            min(int(shot[1:]) for shot in row["source_shot_ids"]), row["event_id"]))
        counters = [row["counter_id"] for row in events if row["counter_id"]]
        if len(set(counters)) != len(counters):
            raise ValueError(f"Counter assigned to multiple event candidates: {code}")
        unassigned = {row["counter_id"] for row in
                      link["unassociated_counter_events"]} - set(counters)
        if len(events) < link["candidate_count_unchanged"]:
            raise ValueError(f"Union lost baseline visual candidates: {code}")
        games.append({
            "official_game_code": code,
            "source_sha256": source,
            "baseline_visual_event_count": link["candidate_count_unchanged"],
            "provisional_event_count": len(events),
            "counter_linked_event_count": len(counters),
            "remaining_unassigned_counter_count": len(unassigned),
            "remaining_unassigned_counter_ids": sorted(unassigned),
            "unassigned_travel_evidence": combined["unassigned_travel_evidence"],
            "candidate_class_counts": dict(sorted(Counter(
                row["candidate_class"] for row in events).items())),
            "colour_conflict_count": sum(
                row["colour_status"] == "conflict" for row in events),
            "events": events,
        })
    return {
        "status": "provisional_source_scoped_event_evidence_union_not_validated_segmentation",
        "input_sha256": {name: digest(path) for name, path in (
            ("linked_visual_events", LINKED), ("travel_proposals", TRAVEL),
            ("travel_origin_relations", RELATIONS), ("held_origin_proposals", HELD),
            ("combine_code", ROOT / "prototype/provisional_event_union.py"),
            ("runner", Path(__file__)))},
        "games": games,
        "limitations": [
            "The event union is a development candidate ledger, not an accepted physical throw timeline.",
            "Adjacent travel cues are attached to counter-linked visual candidates without verifying stone identity.",
            "Travel cues with a possible unlinked visual predecessor remain unassigned rather than creating a duplicate event.",
            "Counter updates are delayed and may be unreadable; release windows are broad and uncertain.",
            "No event has a verified delivered-stone identity, settled board transition, or simulation-ready state.",
            "No independent complete-match physical throw precision, recall or F1 is established.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists():
        if OUTPUT.read_text() != payload:
            raise SystemExit("Existing union differs from current inputs or code")
        print(f"Verified {OUTPUT}")
    else:
        OUTPUT.write_text(payload)
        print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
