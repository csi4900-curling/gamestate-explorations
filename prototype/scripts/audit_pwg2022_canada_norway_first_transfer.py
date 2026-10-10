"""First source-hashed Canada–Norway full-match transfer audit."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.counter_proxy_event_score import score_visual_against_counters
from prototype.official_counter_alignment import align_counter_events

OFFICIAL = ROOT / "validation/official-shot-sequence/pwg2022-canada-norway-official-ledger.json"
PIPELINE = ROOT / "validation/curlobserver-learned-probe/canada-norway-full-transfer"
OUTPUT = (
    ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/FIRST-TRANSFER.json"
)
INPUTS = {
    "counter_replay": PIPELINE / "counter-replay.json",
    "candidate_ledger": PIPELINE / "candidate-event-ledger.json",
    "origin": PIPELINE / "shot-origin.json",
    "cap_decisions": PIPELINE / "two-shot-cap.json",
    "frozen_release": PIPELINE / "frozen-origin-release.json",
}
CLEAN = {"unique_colour_concordant", "unique_colour_concordant_amid_duplicate"}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first transfer result")
    official = json.loads(OFFICIAL.read_text())
    inputs = {key: json.loads(path.read_text()) for key, path in INPUTS.items()}
    source_hash = official["source_video_sha256"]
    if any(row["source_sha256"] != source_hash for row in inputs.values()):
        raise ValueError("Inconsistent source video provenance")
    if inputs["cap_decisions"]["origins_sha256"] != digest(INPUTS["origin"]):
        raise ValueError("Visual decisions do not derive from origin model output")
    counter_events = inputs["counter_replay"]["counter_events"]
    try:
        counter_rows = align_counter_events(official, counter_events)
        counter_alignment_error = None
    except ValueError as error:
        counter_rows = []
        counter_alignment_error = str(error)
    origin_by_id = {row["shot_id"]: row for row in inputs["origin"]["rows"]}
    cap_visual = [
        {
            "shot_id": row["shot_id"],
            "interval_s": origin_by_id[row["shot_id"]]["interval_s"],
            "colour": row["colour"],
        }
        for row in inputs["cap_decisions"]["decisions"]
        if row["status"] == "corroborated_candidate"
    ]
    release_visual = [
        {
            "shot_id": row["shot_id"],
            "interval_s": row["origin_interval_s"],
            "colour": row["unique_passage_colour"],
        }
        for row in inputs["frozen_release"]["rows"]
        if row["unique_passage_colour"] is not None
    ]
    cap_ids = {row["shot_id"] for row in cap_visual}
    combined_visual = cap_visual + [row for row in release_visual if row["shot_id"] not in cap_ids]
    complete_ends = []
    counter_coverage_by_end = []
    if counter_rows:
        for end in official["ends"]:
            clean = [
                row
                for row in counter_rows
                if row["official_end"] == end["end"] and row["status"] in CLEAN
            ]
            counter_coverage_by_end.append(
                {
                    "end": end["end"],
                    "official_shots": len(end["shots"]),
                    "clean_counter_anchors": len(clean),
                    "complete": len(clean) == len(end["shots"]),
                }
            )
            if len(clean) != len(end["shots"]):
                continue
            times = [row["counter_time_s"] for row in clean]
            first, last = min(times), max(times)
            search = lambda items: [
                row for row in items if first - 70 <= row["interval_s"][0] <= last
            ]
            complete_ends.append(
                {
                    "end": end["end"],
                    "counter_span_s": [first, last],
                    "cap_only_score": score_visual_against_counters(search(cap_visual), clean),
                    "cap_plus_release_score": score_visual_against_counters(
                        search(combined_visual), clean
                    ),
                }
            )
    result = {
        "status": "first_frozen_same_family_full_recording_transfer_not_event_f1",
        "source_video_sha256": source_hash,
        "official_ledger_sha256": digest(OFFICIAL),
        "input_sha256": {key: digest(path) for key, path in INPUTS.items()},
        "counter_alignment_code_sha256": digest(ROOT / "prototype/official_counter_alignment.py"),
        "counter_proxy_score_code_sha256": digest(ROOT / "prototype/counter_proxy_event_score.py"),
        "runner_sha256": digest(Path(__file__)),
        "official_shot_count": official["official_shot_count"],
        "candidate_count": inputs["candidate_ledger"]["candidate_count"],
        "counter_event_count": len(counter_events),
        "counter_alignment_error": counter_alignment_error,
        "clean_counter_anchor_count": sum(row["status"] in CLEAN for row in counter_rows),
        "counter_status_counts": {
            status: sum(row["status"] == status for row in counter_rows)
            for status in sorted({row["status"] for row in counter_rows})
        },
        "counter_alignment_rows": counter_rows,
        "counter_coverage_by_end": counter_coverage_by_end,
        "cap_visual_candidate_count": len(cap_visual),
        "frozen_release_candidate_count": len(release_visual),
        "combined_visual_candidate_count": len(combined_visual),
        "complete_counter_anchored_ends": complete_ends,
        "limitations": [
            "Official shot order supplies no video timestamps; candidate count differences are not false-positive or false-negative counts.",
            "Visual-to-counter scores cover only fully clean ends and use a delayed weak proxy, not physical throw labels.",
            "This is one additional recording from the same Beijing 2022 production, not cross-family generalization.",
            "Any counter-reset segmentation failure is preserved rather than repaired after seeing this first transfer.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        {
            key: result[key]
            for key in (
                "official_shot_count",
                "candidate_count",
                "counter_event_count",
                "counter_alignment_error",
                "clean_counter_anchor_count",
                "cap_visual_candidate_count",
                "frozen_release_candidate_count",
            )
        }
    )


if __name__ == "__main__":
    main()
