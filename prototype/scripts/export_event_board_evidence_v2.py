"""Extend provisional event-board handoff with adjacent Swiss state observations."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from event_board_evidence import link_event_boards

BASE = ROOT / "validation/official-shot-sequence"
BOARDS = BASE / "pwg2022-video-partial-board-observations-v2.json"
PRIOR = BASE / "pwg2022-provisional-event-board-evidence.json"
TRANSITIONS = BASE / "swiss-end2-partial-board-transitions-first.json"
LEDGERS = (
    ROOT / "validation/curlobserver-learned-probe/swiss-full-transfer/candidate-event-ledger.json",
    ROOT
    / "validation/curlobserver-learned-probe/china-full-transfer/candidate-throw-event-ledger-after-link.json",
    ROOT
    / "validation/curlobserver-learned-probe/slovakia-full-transfer/candidate-event-ledger.json",
)
OUTPUT = BASE / "pwg2022-provisional-event-board-evidence-v2.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first extended handoff")
    boards, prior, transitions = (
        json.loads(path.read_text()) for path in (BOARDS, PRIOR, TRANSITIONS)
    )
    ledgers = [json.loads(path.read_text()) for path in LEDGERS]
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if reserved["source_sha256"] in {row["source_sha256"] for row in ledgers}:
        raise ValueError("Reserved independent source is not development data")
    if (
        boards["original_export_sha256"]
        != digest(BASE / "pwg2022-video-partial-board-observations.json")
        or transitions["source_sha256"] != ledgers[0]["source_sha256"]
    ):
        raise ValueError("Extended board or transition source mismatch")
    links = link_event_boards(boards["observations"], ledgers)
    if links[: prior["link_count"]] != prior["links"]:
        raise ValueError("Prior seven event-board links changed")
    by_shot = {row["board_observation_id"].split("-video-board-")[-1]: row for row in links}
    paired = []
    for row in transitions["transitions"]:
        if row["status"] != "local_partial_board_comparison":
            continue
        before, after = row["before_shot_id"], row["after_shot_id"]
        if before not in by_shot or after not in by_shot:
            raise ValueError("Transition board missing from event handoff")
        paired.append(
            {
                "before_board_observation_id": by_shot[before]["board_observation_id"],
                "after_board_observation_id": by_shot[after]["board_observation_id"],
                "source_only_transition": row,
            }
        )
    output = {
        "status": "extended_provisional_event_board_sequence_evidence_not_simulation_ready",
        "board_export_sha256": digest(BOARDS),
        "prior_handoff_sha256": digest(PRIOR),
        "source_only_transition_sha256": digest(TRANSITIONS),
        "event_ledger_sha256_by_source": {
            row["source_sha256"]: digest(path) for row, path in zip(ledgers, LEDGERS, strict=True)
        },
        "join_code_sha256": digest(ROOT / "prototype/event_board_evidence.py"),
        "runner_sha256": digest(Path(__file__)),
        "link_count": len(links),
        "unique_shared_counter_count": sum(
            row["link_status"] == "unique_shared_delayed_counter" for row in links
        ),
        "stone_observation_count": sum(row["board_stone_count"] for row in links),
        "adjacent_partial_transition_count": len(paired),
        "links": links,
        "adjacent_partial_transitions": paired,
        "limitations": [
            "Counter-matched event links remain provisional and may select a wrong delivery.",
            "A nearby same-colour stone is a local observation match, not physical identity.",
            "Newly/no-longer observed stones may reflect occlusion or incomplete coverage.",
            "Official diagram comparison is separate and does not alter these video states.",
            "No record is complete, metric-calibrated, or simulation-ready from video alone.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(
        {
            "links": output["link_count"],
            "stones": output["stone_observation_count"],
            "adjacent_transitions": output["adjacent_partial_transition_count"],
        }
    )


if __name__ == "__main__":
    main()
