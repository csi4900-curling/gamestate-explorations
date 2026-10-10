"""Audit broadcast counters and development candidates against official shots."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.official_counter_alignment import align_counter_events

CLEAN_STATUSES = {"unique_colour_concordant", "unique_colour_concordant_amid_duplicate"}

REFERENCE = ROOT / "validation/official-shot-sequence/pwg2022-official-shot-ledger.json"
OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-official-counter-alignment.json"
INPUTS = {
    "PREL000101": (
        "validation/curlobserver-learned-probe/swiss-full-transfer/counter-replay.json",
        "validation/curlobserver-learned-probe/swiss-full-transfer/candidate-event-ledger.json"),
    "PREL000102": (
        "validation/throw-event-benchmark/layout-router/full-china22-counter-postscore-replay.json",
        "validation/curlobserver-learned-probe/china-full-transfer/candidate-throw-event-ledger-v1.json"),
    "PREL000103": (
        "validation/curlobserver-learned-probe/slovakia-full-transfer/counter-replay.json",
        "validation/curlobserver-learned-probe/slovakia-full-transfer/candidate-event-ledger.json"),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first official-counter alignment")
    reference = json.loads(REFERENCE.read_text())
    results = []
    for game in reference["games"]:
        counter_name, candidate_name = INPUTS[game["official_game_code"]]
        counter_path, candidate_path = ROOT / counter_name, ROOT / candidate_name
        counter = json.loads(counter_path.read_text())
        candidates = json.loads(candidate_path.read_text())
        if counter["source_sha256"] != game["source_video_sha256"] or candidates["source_sha256"] != game["source_video_sha256"]:
            raise ValueError("Input ledgers do not refer to the official game video")
        if digest(counter_path) != candidates["counter_audit_sha256"]:
            raise ValueError("Candidate ledger was built from a different counter replay")
        rows = align_counter_events(game, counter["counter_events"])
        by_counter = {row["counter_id"]: row for row in rows}
        candidate_links = []
        for candidate in candidates["events"]:
            counter_id = candidate.get("counter_id")
            if counter_id is None:
                continue
            row = by_counter[counter_id]
            candidate_links.append({
                "candidate_id": candidate["candidate_id"],
                "counter_id": counter_id,
                "official_shot_id": row["official_shot_id"] if row["status"] in CLEAN_STATUSES else None,
                "candidate_colour": candidate.get("colour"),
                "official_colour": row["official_colour"],
                "counter_alignment_status": row["status"],
                "release_window_s": candidate.get("release_window_s"),
                "counter_time_s": row["counter_time_s"],
            })
        candidate_link_counts = Counter(link["official_shot_id"] for link in candidate_links if link["official_shot_id"])
        for link in candidate_links:
            if link["official_shot_id"] and candidate_link_counts[link["official_shot_id"]] > 1:
                link["counter_alignment_status"] = "multiple_candidates_for_official_shot"
                link["official_shot_id"] = None
            elif (link["official_shot_id"] and link["release_window_s"]
                  and link["release_window_s"][0] > link["counter_time_s"] + 1):
                link["counter_alignment_status"] = "candidate_after_counter"
                link["official_shot_id"] = None
            elif link["official_shot_id"] and link["candidate_colour"] is None:
                link["counter_alignment_status"] = "candidate_colour_unknown"
            elif link["official_shot_id"] and link["candidate_colour"] != link["official_colour"]:
                link["counter_alignment_status"] = "candidate_colour_conflict"
        status_counts = Counter(row["status"] for row in rows)
        link_status_counts = Counter(link["counter_alignment_status"] for link in candidate_links)
        results.append({
            "official_game_code": game["official_game_code"],
            "counter_audit_path": counter_name,
            "counter_audit_sha256": digest(counter_path),
            "candidate_ledger_path": candidate_name,
            "candidate_ledger_sha256": digest(candidate_path),
            "official_shot_count": game["official_shot_count"],
            "candidate_count": len(candidates["events"]),
            "counter_event_count": len(rows),
            "counter_status_counts": dict(status_counts),
            "candidate_with_counter_count": len(candidate_links),
            "candidate_without_counter_count": len(candidates["events"]) - len(candidate_links),
            "candidate_link_status_counts": dict(link_status_counts),
            "counter_rows": rows,
            "candidate_links": candidate_links,
        })
    result = {
        "status": "official_shot_order_to_broadcast_counter_diagnostic_not_f1",
        "official_reference_path": str(REFERENCE.relative_to(ROOT)),
        "official_reference_sha256": digest(REFERENCE),
        "alignment_code_sha256": digest(ROOT / "prototype/official_counter_alignment.py"),
        "runner_sha256": digest(Path(__file__)),
        "games": results,
        "limitations": [
            "The broadcast counter updates after a delivery and does not locate its release time.",
            "Counter visibility and recognition are incomplete; unique colour-concordant links support shot identity but do not prove an event or full coverage.",
            "Development candidates used counter evidence, so their counter links are not independent detector validation.",
            "Large upward counter jumps segment ends; this rule must be reviewed if a new recording or unusual graphic differs.",
            "A candidate without a counter can still be a true delivery, and a linked candidate can still have an incorrect release window.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    for row in results:
        print(row["official_game_code"], row["counter_status_counts"], row["candidate_link_status_counts"])


if __name__ == "__main__":
    main()
