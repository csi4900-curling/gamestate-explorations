"""Join independent official shot slots to delayed source-counter candidates."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.counter_slot_alignment import align_counter_slots  # noqa: E402

BASE = ROOT / "validation/curlobserver-learned-probe/korea-china-full-first-transfer"
COUNTERS = BASE / "counter-audit.json"
CANDIDATES = BASE / "candidate-event-ledger.json"
OFFICIAL = ROOT / "validation/official-shot-sequence/pwg2022-korea-china-official-ledger.json"
BOARDS = ROOT / "validation/official-shot-sequence/pwg2022-korea-china-official-boards.json"
OUTPUT = (
    ROOT / "validation/official-shot-sequence/korea-china-official-counter-slot-handoff-first.json"
)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("First slot handoff already exists")
    counters = json.loads(COUNTERS.read_text())
    candidates = json.loads(CANDIDATES.read_text())
    official = json.loads(OFFICIAL.read_text())
    boards = json.loads(BOARDS.read_text())
    if (
        len(
            {
                counters["source_sha256"],
                candidates["source_sha256"],
                official["source_video_sha256"],
                boards["source_video_sha256"],
            }
        )
        != 1
    ):
        raise ValueError("Source-video hash conflict")
    if boards["shot_ledger_sha256"] != digest(OFFICIAL):
        raise ValueError("Official diagram/shot ledger conflict")
    aligned = align_counter_slots(
        counters["counter_events"], official["ends"], official["team_handle_colours"]
    )
    by_counter = {}
    for candidate in candidates["events"]:
        cid = candidate["counter_id"]
        if cid:
            if cid in by_counter:
                raise ValueError("Counter linked to multiple candidates")
            by_counter[cid] = candidate
    by_shot = {shot["official_shot_id"]: shot for end in official["ends"] for shot in end["shots"]}
    by_board = {shot["official_shot_id"]: shot for end in boards["ends"] for shot in end["shots"]}
    if len(by_shot) != 96 or len(by_board) != 96:
        raise ValueError("Official shot or board count changed")
    rows = []
    for slot in aligned["slots"]:
        shot_id = slot["official_shot_id"]
        candidate = by_counter.get(slot["counter_id"])
        board = by_board[shot_id]
        rows.append(
            {
                **slot,
                "official_reference": {
                    "shooter": by_shot[shot_id]["shooter"],
                    "shot_type": by_shot[shot_id]["shot_type"],
                    "turn_direction": by_shot[shot_id]["rotation"],
                    "turn_revolution_count": None,
                    "post_shot_diagram_stones": [
                        {
                            "colour": stone["colour"],
                            "house_radius_coordinates": stone["house_radius_coordinates"],
                        }
                        for stone in board["stones"]
                    ],
                    "diagram_review_flags": board["review_flags"],
                    "diagram_scope": "official schematic area around house, not full rink",
                },
                "video_event_evidence": {
                    "candidate_id": candidate["candidate_id"] if candidate else None,
                    "candidate_camera_shot_id": candidate["shot_id"] if candidate else None,
                    "candidate_evidence_class": candidate["evidence_class"] if candidate else None,
                    "candidate_release_window_s": candidate["release_window_s"]
                    if candidate
                    else None,
                    "candidate_colour": candidate["colour"] if candidate else None,
                    "candidate_colour_status": candidate["colour_status"] if candidate else None,
                    "physical_throw_identity_verified": False,
                    "exact_release_time_s": None,
                    "exact_settle_time_s": None,
                },
                "video_post_shot_board_status": "unobserved",
                "video_physics_simulation_ready": False,
            }
        )
    if len(rows) != 96 or len(by_counter) != aligned["aligned_counter_count"]:
        raise ValueError("Slot/counter/candidate count conflict")
    result = {
        "status": "official_order_diagrams_and_counter_proxy_video_candidates_not_complete_video_state",
        "source_video_sha256": official["source_video_sha256"],
        "input_sha256": {
            "counter_audit": digest(COUNTERS),
            "candidate_ledger": digest(CANDIDATES),
            "official_shots": digest(OFFICIAL),
            "official_boards": digest(BOARDS),
        },
        "alignment_code_sha256": digest(ROOT / "prototype/counter_slot_alignment.py"),
        "runner_sha256": digest(Path(__file__)),
        "official_slot_count": len(rows),
        "counter_linked_slot_count": aligned["aligned_counter_count"],
        "missing_counter_slot_count": aligned["missing_counter_slot_count"],
        "candidate_evidence_class_counts": dict(
            Counter(row["video_event_evidence"]["candidate_evidence_class"] for row in rows)
        ),
        "end_summaries": aligned["end_summaries"],
        "slots": rows,
        "limitations": [
            "The official PDF supplies shot order and schematic post-shot diagrams but no video timestamps.",
            "Counter changes are delayed proxies; a counter-linked candidate is not verified physical throw identity.",
            "Fifteen missing counter slots are left unassigned despite visual-only candidate proposals.",
            "No video-derived board, full-sheet state, metric trajectory, spin count or simulation-ready replay is claimed.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "official_slot_count",
                    "counter_linked_slot_count",
                    "missing_counter_slot_count",
                    "candidate_evidence_class_counts",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
