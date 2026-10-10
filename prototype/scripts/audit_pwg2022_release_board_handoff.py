"""Check direct release-to-partial-board overlap across exposed 2022 matches."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from release_board_handoff import join_release_boards

BASE = ROOT / "validation/official-shot-sequence"
BOARDS = BASE / "pwg2022-provisional-event-board-evidence-v2.json"
UNION = BASE / "pwg2022-provisional-event-evidence-union-development.json"
PASSAGES = {
    "PREL000101": BASE / "swiss-provisional-release-transfer-first.json",
    "PREL000102": BASE / "china-provisional-release-transfer-first.json",
    "PREL000103": BASE / "slovakia-provisional-release-coverage-development.json",
}
OUTPUT = BASE / "pwg2022-release-to-board-handoff-development.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def build():
    boards = json.loads(BOARDS.read_text())
    union = json.loads(UNION.read_text())
    releases = [json.loads(path.read_text()) for path in PASSAGES.values()]
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if any(row["source_video_sha256"] == reserved["source_sha256"] for row in boards["links"]):
        raise ValueError("Reserved board source cannot enter development audit")
    rows = join_release_boards(boards["links"], union["games"], releases)
    return {
        "status": "development_release_to_partial_board_overlap_not_state_transition",
        "input_sha256": {
            "board_handoff": digest(BOARDS),
            "provisional_union": digest(UNION),
            "release_sidecars": {code: digest(path) for code, path in PASSAGES.items()},
        },
        "join_code_sha256": digest(ROOT / "prototype/release_board_handoff.py"),
        "runner_sha256": digest(Path(__file__)),
        "partial_board_count": len(rows),
        "unique_counter_linked_event_count": sum(
            row["event_join_status"] == "unique_shared_counter" for row in rows
        ),
        "boards_with_unique_within_view_release_cue": sum(
            row["release_cue_status"] == "cue_precedes_board" for row in rows
        ),
        "rows": rows,
        "limitations": [
            "A shared delayed counter is provisional bookkeeping, not delivered-stone identity.",
            "A missing release cue in the event's camera shot does not prove that the physical throw was absent.",
            "The nine video boards are partial and have no verified delivered-stone identity or metric calibration.",
            "No physical state transition or simulation-ready output is established.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists():
        if OUTPUT.read_text() != payload:
            raise SystemExit("Existing board/release handoff differs from inputs or code")
        print(f"Verified {OUTPUT}")
    else:
        OUTPUT.write_text(payload)
        print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
