"""Audit v3 candidate-to-official-slot bookkeeping through delayed counters."""

from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/official-shot-sequence"
UNION = BASE / "pwg2022-provisional-event-evidence-union-v3-preorigin-travel-development.json"
ALIGNMENT = BASE / "pwg2022-official-counter-alignment.json"
REFERENCE = BASE / "pwg2022-official-shot-ledger.json"
OUTPUT = BASE / "pwg2022-v3-counter-slot-coverage-development.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def index(rows, key):
    result = {row[key]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"Duplicate {key}")
    return result


def build():
    union = json.loads(UNION.read_text())
    alignment = json.loads(ALIGNMENT.read_text())
    reference = json.loads(REFERENCE.read_text())
    if alignment["official_reference_sha256"] != digest(REFERENCE):
        raise ValueError("Official alignment and reference differ")
    aligned = index(alignment["games"], "official_game_code")
    official = index(reference["games"], "official_game_code")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    games = []
    for game in union["games"]:
        code = game["official_game_code"]
        ref = official[code]
        counter_info = aligned[code]
        source = game["source_sha256"]
        if source == reserved["source_sha256"] or source != ref["source_video_sha256"]:
            raise ValueError("Source mismatch or reserved-source overlap")
        counters = index(counter_info["counter_rows"], "counter_id")
        official_ids = {shot["official_shot_id"] for end in ref["ends"] for shot in end["shots"]}
        event_rows = []
        slot_to_events = defaultdict(list)
        for event in game["events"]:
            counter_id = event["counter_id"]
            if counter_id is None:
                continue
            if counter_id not in counters:
                raise ValueError(f"Event counter missing from official alignment: {counter_id}")
            counter = counters[counter_id]
            shot_id = counter["official_shot_id"]
            if shot_id is not None and shot_id not in official_ids:
                raise ValueError("Counter mapped outside official shot list")
            if shot_id is not None:
                slot_to_events[shot_id].append(event["event_id"])
            event_rows.append(
                {
                    "event_id": event["event_id"],
                    "candidate_class": event["candidate_class"],
                    "counter_id": counter_id,
                    "candidate_colour": event["colour"],
                    "counter_colour": counter["counter_colour"],
                    "official_shot_id": shot_id,
                    "official_colour": counter["official_colour"],
                    "counter_alignment_status": counter["status"],
                    "counter_time_s": counter["counter_time_s"],
                }
            )
        duplicate_slots = [
            {"official_shot_id": slot, "event_ids": sorted(events)}
            for slot, events in sorted(slot_to_events.items())
            if len(events) > 1
        ]
        uncovered = sorted(official_ids - set(slot_to_events))
        by_end = []
        for end in ref["ends"]:
            ids = {shot["official_shot_id"] for shot in end["shots"]}
            by_end.append(
                {
                    "end": end["end"],
                    "official_shot_count": len(ids),
                    "counter_anchored_unique_slot_count": len(ids & set(slot_to_events)),
                    "uncovered_official_slot_ids": sorted(ids - set(slot_to_events)),
                    "duplicate_counter_slot_count": sum(
                        row["official_shot_id"] in ids for row in duplicate_slots
                    ),
                }
            )
        if len(event_rows) != game["counter_linked_event_count"]:
            raise ValueError("Union counter-linked event count differs")
        if (
            len(set(counters) - {row["counter_id"] for row in event_rows})
            != game["remaining_unassigned_counter_count"]
        ):
            raise ValueError("Union unassigned counter count differs")
        games.append(
            {
                "recording_code": code,
                "source_sha256": source,
                "official_shot_count": len(official_ids),
                "provisional_event_count": game["provisional_event_count"],
                "counter_linked_event_count": len(event_rows),
                "counter_anchored_unique_official_slot_count": len(slot_to_events),
                "uncovered_official_slot_count": len(uncovered),
                "uncovered_official_slot_ids": uncovered,
                "duplicate_counter_slot_count": len(duplicate_slots),
                "duplicate_counter_slots": duplicate_slots,
                "noncounter_candidate_count": sum(
                    event["counter_id"] is None for event in game["events"]
                ),
                "counter_alignment_status_counts": dict(
                    sorted(Counter(row["counter_alignment_status"] for row in event_rows).items())
                ),
                "ends": by_end,
                "counter_linked_events": event_rows,
            }
        )
    return {
        "status": "development_v3_counter_to_official_slot_proxy_not_physical_f1",
        "input_sha256": {
            "v3_union": digest(UNION),
            "counter_alignment": digest(ALIGNMENT),
            "official_reference": digest(REFERENCE),
            "runner": digest(Path(__file__)),
        },
        "official_shot_count": sum(g["official_shot_count"] for g in games),
        "provisional_event_count": sum(g["provisional_event_count"] for g in games),
        "counter_linked_event_count": sum(g["counter_linked_event_count"] for g in games),
        "counter_anchored_unique_official_slot_count": sum(
            g["counter_anchored_unique_official_slot_count"] for g in games
        ),
        "uncovered_official_slot_count": sum(g["uncovered_official_slot_count"] for g in games),
        "duplicate_counter_slot_count": sum(g["duplicate_counter_slot_count"] for g in games),
        "noncounter_candidate_count": sum(g["noncounter_candidate_count"] for g in games),
        "games": games,
        "limitations": [
            "An uncovered official slot can still have a real video event without a readable delayed counter; it is not a physical false negative label.",
            "Several counters can map to one official slot because broadcast graphics flicker or the proxy alignment is ambiguous.",
            "A counter-linked candidate is not verified as the physical official shot, even when its colour agrees.",
            "Official shot lists have no physical video timestamps; these counts are not event precision, recall, or F1.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists() and OUTPUT.read_text() != payload:
        raise SystemExit("Existing v3 slot audit differs from hashed inputs")
    if not OUTPUT.exists():
        OUTPUT.write_text(payload)
    print(f"Verified {OUTPUT}")


if __name__ == "__main__":
    main()
