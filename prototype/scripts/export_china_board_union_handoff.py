"""Link China partial-board windows to the provisional event union."""

from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/official-shot-sequence"
BOARDS = BASE / "china-board-event-coverage-v1.json"
UNION = BASE / "pwg2022-provisional-event-evidence-union-development.json"
OUTPUT = BASE / "china-board-event-union-handoff-development.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def temporal_relation(board_window, travel_window):
    if board_window is None or travel_window is None:
        return "no_comparable_travel_interval"
    if min(board_window[1], travel_window[1]) >= max(board_window[0], travel_window[0]):
        return "overlaps_observed_travel_interval"
    return ("board_observation_after_travel" if board_window[0] > travel_window[1]
            else "board_observation_before_travel")


def build():
    boards = json.loads(BOARDS.read_text())
    union = json.loads(UNION.read_text())
    china = next(row for row in union["games"]
                 if row["official_game_code"] == "PREL000102")
    source = boards["source_sha256"]
    if china["source_sha256"] != source:
        raise ValueError("Board and event video sources differ")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source == reserved["source_sha256"]:
        raise ValueError("Reserved source selected")
    by_counter = {row["counter_id"]: row for row in china["events"]
                  if row["counter_id"] is not None}
    if len(by_counter) != china["counter_linked_event_count"]:
        raise ValueError("Union counter uniqueness differs")
    rows = []
    for board in boards["rows"]:
        counter = board["legacy_event"]["counter_id"]
        event = by_counter.get(counter)
        travel_window = event["observed_travel_window_s"] if event else None
        rows.append({
            "board_window_id": board["board_window_id"],
            "source_video_sha256": source,
            "counter_id": counter,
            "counter_anchor_s": board["counter_anchor_s"],
            "partial_board_stone_count": board["partial_board_stone_count"],
            "board_observation_interval_s": board["board_observation_interval_s"],
            "board_stones": board["board_stones"],
            "event_coverage": "unique_counter_linked_candidate" if event else
                              "no_counter_linked_candidate",
            "event": ({
                "event_id": event["event_id"],
                "candidate_class": event["candidate_class"],
                "source_shot_ids": event["source_shot_ids"],
                "colour": event["colour"],
                "colour_status": event["colour_status"],
                "delivery_window_s": event["delivery_window_s"],
                "observed_travel_window_s": travel_window,
                "has_held_origin_cue": event["attached_held_evidence"] is not None,
            } if event else None),
            "board_travel_timing_relation": temporal_relation(
                board["board_observation_interval_s"], travel_window),
            "delivered_stone_to_board_identity_verified": False,
            "physical_state_transition_verified": False,
            "simulation_ready": False,
        })
    return {
        "status": "development_counter_joined_partial_board_handoff_not_state_reconstruction",
        "source_sha256": source,
        "input_sha256": {"board_windows": digest(BOARDS),
                         "provisional_event_union": digest(UNION),
                         "runner": digest(Path(__file__))},
        "window_count": len(rows),
        "partial_board_window_count": sum(row["partial_board_stone_count"] > 0 for row in rows),
        "partial_board_windows_with_event": sum(
            row["partial_board_stone_count"] > 0 and
            row["event_coverage"] == "unique_counter_linked_candidate" for row in rows),
        "partial_board_windows_overlapping_travel": sum(
            row["partial_board_stone_count"] > 0 and
            row["board_travel_timing_relation"] == "overlaps_observed_travel_interval"
            for row in rows),
        "rows": rows,
        "limitations": [
            "The join shares a delayed counter; it is not independent verification of physical throw identity.",
            "Temporal overlap of a travel track and partial board does not prove the same object was observed.",
            "All boards remain incomplete and unitless; no settled physical transition is established.",
            "No record is simulation-ready and no complete-match event F1 follows from these links.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists():
        if OUTPUT.read_text() != payload:
            raise SystemExit("Existing board handoff differs from current inputs or code")
        print(f"Verified {OUTPUT}")
    else:
        OUTPUT.write_text(payload)
        print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
