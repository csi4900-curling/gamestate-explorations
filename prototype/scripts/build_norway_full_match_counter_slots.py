"""Freeze official-order slots and source counter coverage for Norway match."""

from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from prototype.counter_slot_alignment import align_counter_slots


BASE = ROOT / "validation/curlobserver-learned-probe/canada-norway-full-transfer"
COUNTERS = BASE / "counter-audit.json"
CANDIDATES = BASE / "fused-linked.json"
OFFICIAL = ROOT / "validation/official-shot-sequence/pwg2022-canada-norway-official-ledger.json"
RESCUES = ROOT / "validation/official-shot-sequence/norway-unlinked-motion-rescue-proposals-first.json"
OUTPUT = ROOT / "validation/official-shot-sequence/norway-full-match-official-counter-slot-scaffold-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first full-match counter-slot scaffold")
    counters = json.loads(COUNTERS.read_text())
    candidates = json.loads(CANDIDATES.read_text())
    official = json.loads(OFFICIAL.read_text())
    rescues = json.loads(RESCUES.read_text())
    if len({counters["source_sha256"], candidates["source_sha256"],
            official["source_video_sha256"]}) != 1:
        raise SystemExit("Counter, candidate, and official source videos disagree")
    aligned = align_counter_slots(counters["counter_events"], official["ends"],
                                  official["team_handle_colours"])
    by_counter = {}
    for event in candidates["events"]:
        counter_id = event["counter_id"]
        if counter_id is None:
            continue
        if counter_id in by_counter:
            raise ValueError(f"Duplicate candidate counter link: {counter_id}")
        by_counter[counter_id] = event
    rows = []
    for slot in aligned["slots"]:
        candidate = by_counter.get(slot["counter_id"])
        rows.append({**slot,
                     "video_candidate_shot_id": candidate["shot_id"] if candidate else None,
                     "provisional_delivery_window_s": candidate["delivery_window_s"] if candidate else None,
                     "candidate_colour": candidate["colour"] if candidate else None,
                     "candidate_colour_relation": (
                         "unknown" if candidate is None or candidate["colour"] is None else
                         "agrees" if candidate["colour"] == slot["official_colour"] else "conflicts"),
                     "source_rescue_proposal": False,
                     "simulation_ready": False})
    rescue = [row for row in rescues["proposals"] if row["origin_shot_id"] == "S86"]
    if len(rescue) != 1:
        raise SystemExit("S86 source proposal changed")
    final_first_end = next(row for row in rows if row["end"] == 1 and row["shot_number"] == 16)
    if final_first_end["counter_id"] is not None or final_first_end["official_colour"] != "yellow":
        raise SystemExit("First end final shot is no longer a missing yellow counter slot")
    final_first_end.update({
        "video_candidate_shot_id": "S86",
        "provisional_delivery_window_s": [rescue[0]["origin_interval_s"][0],
                                          rescue[0]["receiving_motion_interval_s"][1]],
        "candidate_colour": "yellow",
        "candidate_colour_relation": "agrees",
        "source_rescue_proposal": True,
        "receiving_episode_id": rescue[0]["receiving_episode_id"],
    })
    counter_only = [row["counter_id"] for row in rows
                    if row["counter_id"] is not None and row["video_candidate_shot_id"] is None]
    if len(rows) != official["official_shot_count"] or aligned["aligned_counter_count"] != len(counters["counter_events"]):
        raise SystemExit("Official/counter scaffold count disagreement")
    output = {
        "status": "independent_official_order_plus_broadcast_counter_proxy_not_verified_video_events",
        "input_sha256": {"counter_audit": digest(COUNTERS),
                         "candidate_ledger": digest(CANDIDATES),
                         "official_shot_ledger": digest(OFFICIAL),
                         "unlinked_motion_rescue_proposals": digest(RESCUES)},
        "alignment_code_sha256": digest(ROOT / "prototype/counter_slot_alignment.py"),
        "runner_sha256": digest(Path(__file__)),
        "official_shot_slot_count": len(rows),
        "aligned_counter_count": aligned["aligned_counter_count"],
        "missing_counter_slot_count": aligned["missing_counter_slot_count"],
        "counter_backed_candidate_link_count": sum(row["counter_id"] is not None and
                                                   row["video_candidate_shot_id"] is not None for row in rows),
        "counter_only_ids": counter_only,
        "source_rescue_proposal_count": sum(row["source_rescue_proposal"] for row in rows),
        "provisional_candidate_colour_conflict_count": sum(
            row["candidate_colour_relation"] == "conflicts" for row in rows),
        "end_summaries": aligned["end_summaries"],
        "slots": rows,
        "limitations": [
            "The official PDF establishes shot order and team colour, not video timestamps or physical stone identity.",
            "Broadcast remaining-stone decrements occur after throws and can be absent; aligned slots are counter proxies.",
            "Missing counter slots are not automatically filled with candidate windows.",
            "The S86 final-end-one link is a source-development proposal, not independent event validation.",
            "No complete video game state, exact release/settle time, event F1, or simulation-ready output is claimed.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print({key: output[key] for key in
           ("official_shot_slot_count", "aligned_counter_count", "missing_counter_slot_count",
            "counter_backed_candidate_link_count", "counter_only_ids",
            "source_rescue_proposal_count", "provisional_candidate_colour_conflict_count")})


if __name__ == "__main__":
    main()
