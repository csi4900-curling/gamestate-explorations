"""Export broadcast-counter consistency for visual-only event proposals."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from visual_counter_gap_screen import screen_visual_counter_gaps  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--counter-replay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Counter-gap audit already exists")
    ledger = json.loads(args.ledger.read_text())
    counters = json.loads(args.counter_replay.read_text())
    for field in ("source_sha256", "source_interval_s"):
        if ledger[field] != counters[field]:
            parser.error(f"Input {field} mismatch")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if ledger["source_sha256"] == reserved["source_sha256"]:
        parser.error("Reserved source cannot be used for development audit")
    result = screen_visual_counter_gaps(ledger["events"], counters["counter_events"])
    result.update(
        {
            "status": "development_visual_only_counter_consistency_not_event_truth",
            "source_sha256": ledger["source_sha256"],
            "source_interval_s": ledger["source_interval_s"],
            "ledger_sha256": file_sha256(args.ledger),
            "counter_replay_sha256": file_sha256(args.counter_replay),
            "screen_code_sha256": file_sha256(ROOT / "prototype/visual_counter_gap_screen.py"),
            "runner_sha256": file_sha256(__file__),
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["status_counts"])


if __name__ == "__main__":
    main()
