"""Join sequence discrepancies to source evidence for targeted video review."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/official-shot-sequence"
SEQUENCE = BASE / "pwg2022-v3-official-sequence-diagnostic-development.json"
HANDOFF = BASE / "pwg2022-event-evidence-handoff-v3-development.json"
SEGMENTS = BASE / "pwg2022-full-match-event-review-segments-v3-preorigin-travel-development.json"
OUTPUT = BASE / "pwg2022-v3-sequence-review-queue-development.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def indexed(rows, key):
    result = {row[key]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"Duplicate {key}")
    return result


def build():
    audit = json.loads(SEQUENCE.read_text())
    handoff = json.loads(HANDOFF.read_text())
    segments = json.loads(SEGMENTS.read_text())
    handoff_games = indexed(handoff["games"], "recording_code")
    segment_games = indexed(segments["games"], "official_game_code")
    rows = []
    for game in audit["games"]:
        code = game["recording_code"]
        evidence_game = handoff_games[code]
        segment_game = segment_games[code]
        if (
            game["source_sha256"] != evidence_game["source_sha256"]
            or game["source_sha256"] != segment_game["source_sha256"]
        ):
            raise ValueError("Source hashes differ")
        evidence = indexed(evidence_game["rows"], "event_id")
        windows = indexed(segment_game["segments"], "event_id")
        for end in game["ends"]:
            candidates = end["candidate_rows"]
            official = end["official_rows"]
            for index, candidate in enumerate(candidates):
                if candidate["status"] != "skipped_in_every_optimum":
                    continue
                event_id = candidate["candidate_id"]
                event = evidence[event_id]
                window = windows[event_id]
                release = event["release_cue"]
                rows.append(
                    {
                        "kind": "candidate_skipped_in_every_optimum",
                        "recording_code": code,
                        "end": end["end"],
                        "event_id": event_id,
                        "ledger_colour": event["event_colour"],
                        "counter_id": event["counter_id"],
                        "release_cue_status": release["status"],
                        "source_release_cue_colour": release["colour"],
                        "source_release_cue_time_s": release["time_s"],
                        "receiving_view_status": event["receiving_view"]["status"],
                        "receiving_view_colour": event["receiving_view"]["colour"],
                        "previous_candidate_id": candidates[index - 1]["candidate_id"]
                        if index
                        else None,
                        "next_candidate_id": candidates[index + 1]["candidate_id"]
                        if index + 1 < len(candidates)
                        else None,
                        "source_video_path": segment_game["source_video_path"],
                        "review_window_s": window["review_window_s"],
                        "priority": "protect_source_release_cue"
                        if release["status"] == "unique_passage"
                        else "inspect_duplicate_or_sequence_assumption",
                    }
                )
            for index, shot in enumerate(official):
                if shot["status"] != "unmatched_in_every_optimum":
                    continue
                before = next(
                    (
                        prior["unique_candidate_id"]
                        for prior in reversed(official[:index])
                        if prior["unique_candidate_id"] is not None
                    ),
                    None,
                )
                after = next(
                    (
                        later["unique_candidate_id"]
                        for later in official[index + 1 :]
                        if later["unique_candidate_id"] is not None
                    ),
                    None,
                )
                rows.append(
                    {
                        "kind": "official_slot_unmatched_in_every_optimum",
                        "recording_code": code,
                        "end": end["end"],
                        "official_shot_id": shot["official_shot_id"],
                        "previous_official_shot_id": official[index - 1]["official_shot_id"]
                        if index
                        else None,
                        "next_official_shot_id": official[index + 1]["official_shot_id"]
                        if index + 1 < len(official)
                        else None,
                        "source_video_path": segment_game["source_video_path"],
                        "preceding_matched_candidate_id": before,
                        "preceding_candidate_review_window_s": windows[before]["review_window_s"]
                        if before
                        else None,
                        "following_matched_candidate_id": after,
                        "following_candidate_review_window_s": windows[after]["review_window_s"]
                        if after
                        else None,
                        "priority": "inspect_neighbouring_video_not_a_labeled_miss",
                    }
                )
    counts = Counter(row["kind"] for row in rows)
    protected = [
        row["event_id"]
        for row in rows
        if row["kind"] == "candidate_skipped_in_every_optimum"
        and row["priority"] == "protect_source_release_cue"
    ]
    if counts != {
        "candidate_skipped_in_every_optimum": 15,
        "official_slot_unmatched_in_every_optimum": 10,
    } or sorted(protected) != sorted(["VISUAL-S243", "VISUAL-S593", "VISUAL-S60", "VISUAL-S282"]):
        raise ValueError("Review queue counts or release-cue safeguards changed")
    return {
        "status": "development_postscore_review_queue_not_physical_labels",
        "input_sha256": {
            "sequence": digest(SEQUENCE),
            "handoff": digest(HANDOFF),
            "review_segments": digest(SEGMENTS),
            "runner": digest(Path(__file__)),
        },
        "row_count": len(rows),
        "kind_counts": dict(counts),
        "source_release_cue_present_in_skipped_candidates": len(protected),
        "source_release_cue_event_ids": protected,
        "rows": rows,
        "limitations": [
            "Skip and gap statuses depend on the official-order proxy and edit costs; neither is an independent event label.",
            "A unique release passage supports review but does not prove a distinct physical throw.",
            "Official shot pages have no source-video timestamps, so unmatched slots have no exact review interval.",
            "Counter links and matching colours do not verify cross-camera physical stone identity.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists() and OUTPUT.read_text() != payload:
        raise SystemExit("Existing review queue differs from hashed inputs")
    if not OUTPUT.exists():
        OUTPUT.write_text(payload)
    print(f"Verified {OUTPUT}")


if __name__ == "__main__":
    main()
