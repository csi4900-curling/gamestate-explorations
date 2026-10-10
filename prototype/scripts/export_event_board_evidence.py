"""Join partial video boards to provisional events via shared delayed counters."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from event_board_evidence import link_event_boards

BOARD = ROOT / "validation/official-shot-sequence/pwg2022-video-partial-board-observations.json"
LEDGERS = (
    ROOT / "validation/curlobserver-learned-probe/swiss-full-transfer/candidate-event-ledger.json",
    ROOT / "validation/curlobserver-learned-probe/china-full-transfer/candidate-throw-event-ledger-after-link.json",
    ROOT / "validation/curlobserver-learned-probe/slovakia-full-transfer/candidate-event-ledger.json",
)
OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-provisional-event-board-evidence.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first event-board export")
    board_data = json.loads(BOARD.read_text())
    ledgers = [json.loads(path.read_text()) for path in LEDGERS]
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if reserved["source_sha256"] in {row["source_sha256"] for row in ledgers}:
        raise ValueError("Reserved independent source is not development data")
    links = link_event_boards(board_data["observations"], ledgers)
    output = {
        "status": "provisional_video_event_to_partial_board_evidence_not_simulation_ready",
        "board_input_sha256": digest(BOARD),
        "event_ledger_sha256_by_source": {
            row["source_sha256"]: digest(path)
            for row, path in zip(ledgers, LEDGERS, strict=True)},
        "join_code_sha256": digest(ROOT / "prototype/event_board_evidence.py"),
        "runner_sha256": digest(Path(__file__)),
        "link_count": len(links),
        "unique_shared_counter_count": sum(
            row["link_status"] == "unique_shared_delayed_counter" for row in links),
        "stone_observation_count": sum(row["board_stone_count"] for row in links),
        "links": links,
        "limitations": [
            "A shared delayed counter timestamp is a bookkeeping link, not physical throw identity.",
            "The boards are selected partial observations, not a continuous game-state sequence.",
            "A local stone observation cannot be assigned to the delivered event without tracking.",
            "Metric scale, settle time, persistent IDs, and full trajectory are unvalidated.",
            "No linked record is simulation-ready.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print({"links": output["link_count"],
           "unique_counter_links": output["unique_shared_counter_count"],
           "stones": output["stone_observation_count"]})


if __name__ == "__main__":
    main()
