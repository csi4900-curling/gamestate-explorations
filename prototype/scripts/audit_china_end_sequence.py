"""Recount reviewed China 2024 candidate events by source-observed ends.

This is a development audit. The four exclusions and seven end boundaries were
chosen after source review; they are not independent ground truth.
"""

import hashlib
import json
from collections import Counter
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.event_sequence_consistency import audit_end_sequence

TIMELINE = (
    ROOT
    / "validation/throw-event-benchmark/layout-router/full-2024-coverage/new-preflight-china24/timeline.json"
)
REVIEW = ROOT / "validation/official-shot-sequence/china-event-catalog-review.json"
OUTPUT = ROOT / "validation/official-shot-sequence/china-end-count-audit.json"
SOURCE = ROOT / "validation/source-cache/Y_U6gzqORUs-360p.mp4"
SOURCE_SHA256 = "51d300ede336efdd8d39029f8728c9d7cac3dd0fcfdc96eb7b84832d80753e82"
FIRST_EVENT_BY_END = (
    "R01-S05",
    "R01-S37",
    "R01-S63",
    "R01-S94",
    "R01-S124",
    "R01-S150",
    "R01-S186",
    "R01-S221",
)
BOUNDARY_REVIEW_TIMES_S = (1047.2, 1835.3, 2865.8, 3893.3, 4940.0, 5962.7, 7148.6)


def file_digest(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    if SOURCE.exists() and file_digest(SOURCE) != SOURCE_SHA256:
        raise ValueError("Source video hash differs from reviewed source")
    timeline = json.loads(TIMELINE.read_text())
    review = json.loads(REVIEW.read_text())
    excluded = tuple(
        row["event_id"]
        for row in review["reviewed_nonstone_tracks"]
        if row["event_assessment"] == "likely_false_event"
    )
    original = timeline["observed_events"]
    original_ids = {event["id"] for event in original}
    assert len(excluded) == 4 and set(excluded) <= original_ids
    events = [event for event in original if event["id"] not in excluded]
    positions = [
        next(i for i, event in enumerate(events) if event["id"] == event_id)
        for event_id in FIRST_EVENT_BY_END
    ]
    assert positions == sorted(positions) and positions[0] == 0

    ends = []
    for index, start in enumerate(positions):
        section = events[start : positions[index + 1] if index + 1 < len(positions) else None]
        colours = Counter(event["colour"] for event in section)
        ends.append(
            {
                "end": index + 1,
                "first_event_id": section[0]["id"],
                "last_event_id": section[-1]["id"],
                "first_crossing_s": section[0]["crossing_time_s"],
                "last_crossing_s": section[-1]["crossing_time_s"],
                "candidate_count": len(section),
                "candidate_colour_counts": {
                    colour: colours[colour] for colour in ("red", "yellow")
                },
            }
        )
    assert [end["candidate_count"] for end in ends] == [16] * 7 + [15]
    assert [end["candidate_colour_counts"] for end in ends] == [
        {"red": 8, "yellow": 8} for _ in range(7)
    ] + [{"red": 8, "yellow": 7}]
    assert sum(end["candidate_count"] for end in ends) == len(events) == 127
    raw_end_audit = audit_end_sequence(
        original, BOUNDARY_REVIEW_TIMES_S, timeline["coverage_gaps_s"]
    )
    reviewed_end_audit = audit_end_sequence(
        events, BOUNDARY_REVIEW_TIMES_S, timeline["coverage_gaps_s"]
    )
    assert [row["candidate_count"] for row in reviewed_end_audit] == [
        row["candidate_count"] for row in ends
    ]
    assert [row["first_event_id"] for row in reviewed_end_audit] == list(FIRST_EVENT_BY_END)

    result = {
        "status": "source_reviewed_development_audit_not_independent_event_reference",
        "timeline_path": str(TIMELINE.relative_to(ROOT)),
        "timeline_sha256": hashlib.sha256(TIMELINE.read_bytes()).hexdigest(),
        "audit_code_sha256": file_digest(ROOT / "prototype/event_sequence_consistency.py"),
        "runner_sha256": file_digest(Path(__file__)),
        "source_review_path": str(REVIEW.relative_to(ROOT)),
        "source_review_sha256": hashlib.sha256(REVIEW.read_bytes()).hexdigest(),
        "source_id": timeline["source_id"],
        "source_video_sha256": SOURCE_SHA256,
        "original_candidate_count": len(original),
        "source_reviewed_likely_nonstone_event_ids": list(excluded),
        "reviewed_candidate_count": len(events),
        "boundary_review_times_s": list(BOUNDARY_REVIEW_TIMES_S),
        "raw_end_sequence_diagnostics": raw_end_audit,
        "reviewed_end_sequence_diagnostics": reviewed_end_audit,
        "ends": ends,
        "final_play_review": {
            "last_event_id": "R01-S239",
            "last_event_crossing_s": 7914.54,
            "source_frame_times_s": [7908, 7912, 7916, 7920, 7924, 7928, 7932, 7940, 7950],
            "source_sheet": "validation/official-shot-sequence/china-final-play-sequence.jpg",
            "observation": "Last red stone moves into the house; teams gather and broadcast closes without another visible delivery.",
        },
        "limitations": [
            "Four false-event judgments and end boundaries are source-reviewed by the same investigator who examined predictions.",
            "The balanced end counts do not rule out mutually cancelling false and missed events or wrong colours.",
            "End eight has 15 visible provisional events; the match concludes after the final red event, so 16 deliveries is not a valid count target here.",
            "A source-linked exhaustive independent event reference is still required for precision, recall and F1.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        f"{OUTPUT.relative_to(ROOT)}: {len(original)} candidates, {len(events)} after exclusions; end counts {[e['candidate_count'] for e in ends]}"
    )


if __name__ == "__main__":
    main()
