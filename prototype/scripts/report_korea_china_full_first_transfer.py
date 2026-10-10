"""Summarize the first frozen full-source Korea–China transfer without F1."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/curlobserver-learned-probe/korea-china-full-first-transfer"
OFFICIAL = ROOT / "validation/official-shot-sequence/pwg2022-korea-china-official-ledger.json"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-korea-china/source.mp4"
OUTPUT = ROOT / "validation/throw-event-benchmark/paralympics-2022-korea-china/FIRST-TRANSFER.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("First transfer result already exists")
    paths = {name: BASE / f"{name}.json" for name in
             ("hard-cuts", "counter-audit", "shot-origin", "cap-motion",
              "selected-learned-motion", "fused-linked", "travel-only",
              "candidate-event-ledger")}
    data = {name: json.loads(path.read_text()) for name, path in paths.items()}
    official = json.loads(OFFICIAL.read_text())
    source_hash = digest(VIDEO)
    if source_hash != official["source_video_sha256"] or any(
            row["source_sha256"] != source_hash for row in data.values()):
        raise ValueError("Source-video hash conflict")
    intervals = {tuple(row["source_interval_s"]) for row in data.values()}
    if intervals != {(0, 6829)}:
        raise ValueError(f"Source interval conflict: {intervals}")
    candidates = data["candidate-event-ledger"]["events"]
    counters = data["counter-audit"]["counter_events"]
    if len(candidates) != data["candidate-event-ledger"]["candidate_count"]:
        raise ValueError("Candidate count conflict")
    if official["official_shot_count"] != 96:
        raise ValueError("Official shot count changed")
    counter_ids = {row["id"] for row in counters}
    used_counter_ids = [row["counter_id"] for row in candidates if row["counter_id"]]
    if len(used_counter_ids) != len(set(used_counter_ids)) or not set(used_counter_ids) <= counter_ids:
        raise ValueError("Counter-to-candidate association is not one-to-one")
    result = {
        "status": "frozen_first_full_match_transfer_count_and_coverage_not_event_f1",
        "source_video_sha256": source_hash,
        "source_interval_s": [0, 6829],
        "source_tail_not_processed_s": 0.666667,
        "official_pdf_sha256": official["official_pdf_sha256"],
        "official_shot_count": official["official_shot_count"],
        "official_end_shot_counts": [end["shot_count"] for end in official["ends"]],
        "candidate_count": len(candidates),
        "candidate_minus_official_count": len(candidates) - official["official_shot_count"],
        "candidate_evidence_class_counts": dict(Counter(row["evidence_class"] for row in candidates)),
        "candidate_colour_counts": dict(Counter(row["colour"] for row in candidates)),
        "candidate_colour_status_counts": dict(Counter(row["colour_status"] for row in candidates)),
        "readable_counter_update_count": len(counters),
        "counter_linked_candidate_count": len(used_counter_ids),
        "unlinked_counter_update_count": len(counter_ids - set(used_counter_ids)),
        "unresolved_counter_change_count": len(data["counter-audit"]["unresolved_counter_changes"]),
        "fused_colour_conflict_count": len(data["fused-linked"]["conflicts"]),
        "stage_sha256": {name: digest(path) for name, path in paths.items()},
        "official_ledger_sha256": digest(OFFICIAL),
        "runner_sha256": digest(Path(__file__)),
        "limitations": [
            "The pipeline covers 0–6829 s of a 6829.667 s file; the final 0.667 s is unprocessed.",
            "Candidate count minus official shot count cannot classify individual false events or misses.",
            "Broadcast counter decrements are delayed proxy evidence and can be unreadable or absent.",
            "Official shot pages lack video timestamps; independent physical throw precision, recall and F1 are not measured.",
            "This is a new match in the same Beijing 2022 broadcast family, not a cross-production transfer.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in
                      ("official_shot_count", "candidate_count", "candidate_minus_official_count",
                       "readable_counter_update_count", "counter_linked_candidate_count",
                       "fused_colour_conflict_count")}, indent=2))


if __name__ == "__main__":
    main()
