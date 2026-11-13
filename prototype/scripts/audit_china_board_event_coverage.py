"""Reproduce the China event-to-board coverage audit across two ledgers."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from event_board_coverage import audit_board_event_coverage

BASE = ROOT / "validation/official-shot-sequence"
CHINA = ROOT / "validation/curlobserver-learned-probe/china-full-transfer"
SCAN = BASE / "china-end2-adjacent-video-boards-first.json"
HANDOFF = BASE / "pwg2022-provisional-event-board-evidence-v2.json"
LEGACY = CHINA / "candidate-throw-event-ledger-after-link.json"
GROUNDED = CHINA / "event-grounding-envelope-v1.json"
OUTPUT = BASE / "china-board-event-coverage-v1.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def build():
    scan, handoff, legacy, grounded = (
        json.loads(path.read_text()) for path in (SCAN, HANDOFF, LEGACY, GROUNDED)
    )
    source = scan["source_sha256"]
    if source != legacy["source_sha256"] or source != grounded["source_sha256"]:
        raise ValueError("Event and board sources differ")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source == reserved["source_sha256"]:
        raise ValueError("Reserved independent recording selected")
    windows = [
        {
            "board_window_id": row["shot_id"],
            "board_source": "first_adjacent_scan",
            "source_video_sha256": source,
            "counter_anchor_s": row["counter_anchor_s"],
            "board_observation_interval_s": (
                [
                    min(stone["first_seen_s"] for stone in row["stable_partial_board"]),
                    max(stone["last_seen_s"] for stone in row["stable_partial_board"]),
                ]
                if row["stable_partial_board"]
                else None
            ),
            "partial_board_stone_count": len(row["stable_partial_board"]),
            "board_stones": row["stable_partial_board"],
        }
        for row in scan["rows"]
    ]
    windows.extend(
        {
            "board_window_id": row["board_observation_id"],
            "board_source": "original_partial_board_export",
            "source_video_sha256": source,
            "counter_anchor_s": row["counter_anchor_s"],
            "board_observation_interval_s": row["board_observation_interval_s"],
            "partial_board_stone_count": row["board_stone_count"],
            "board_stones": row["board_stones"],
        }
        for row in handoff["links"]
        if row["source_video_sha256"] == source
    )
    if len(windows) != 8 or sum(row["partial_board_stone_count"] > 0 for row in windows) != 5:
        raise ValueError("Selected China board windows changed")
    rows = audit_board_event_coverage(windows, legacy["events"], grounded["events"])
    return {
        "status": "source_scoped_development_board_event_coverage_not_state_transition",
        "source_sha256": source,
        "input_sha256": {
            name: digest(path)
            for name, path in (
                ("adjacent_scan", SCAN),
                ("prior_handoff", HANDOFF),
                ("legacy_event_ledger", LEGACY),
                ("grounded_event_envelope", GROUNDED),
                ("join_code", ROOT / "prototype/event_board_coverage.py"),
                ("runner", Path(__file__)),
            )
        },
        "window_count": len(rows),
        "windows_with_partial_board": sum(row["partial_board_stone_count"] > 0 for row in rows),
        "partial_board_stone_count": sum(row["partial_board_stone_count"] for row in rows),
        "grounded_event_present_count": sum(
            row["grounded_event_coverage"] == "present" for row in rows
        ),
        "board_windows_missing_grounded_event_count": sum(
            row["partial_board_stone_count"] > 0 and row["grounded_event_coverage"] == "absent"
            for row in rows
        ),
        "rows": rows,
        "limitations": [
            "Exact shared delayed-counter time is a bookkeeping join, not physical stone identity.",
            "The grounded envelope is a 112-candidate cap-fusion subset, not the full legacy event ledger.",
            "An absent grounded event cannot be treated as absence of a physical throw.",
            "All boards are partial; there is no verified physical state transition or simulation-ready state.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists():
        if OUTPUT.read_text() != payload:
            raise SystemExit("Existing audit differs from current inputs or code")
        print(f"Verified {OUTPUT}")
    else:
        OUTPUT.write_text(payload)
        print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
