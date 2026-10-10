"""Build a source-linked candidate throw sequence from visual and counter evidence."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from prototype.throw_event_ledger import build_throw_event_ledger


ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fused-events", required=True, type=Path)
    parser.add_argument("--travel-only", required=True, type=Path)
    parser.add_argument("--counter-audit", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first candidate ledger")
    fused = json.loads(args.fused_events.read_text())
    travel = json.loads(args.travel_only.read_text())
    counter = json.loads(args.counter_audit.read_text())
    if any(source["source_sha256"] != fused["source_sha256"] or
           source["source_interval_s"] != fused["source_interval_s"]
           for source in (travel, counter)):
        parser.error("Evidence sources or intervals differ")
    if travel["fused_events_sha256"] != digest(args.fused_events):
        parser.error("Travel-only candidates do not derive from these fused events")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if fused["source_sha256"] == reserved["source_sha256"]:
        parser.error("Reserved independent source cannot be used for development")
    ledger = build_throw_event_ledger(fused["events"], travel["rows"],
                                      counter["counter_events"])
    result = {
        "status": "development_candidate_throw_event_ledger_not_validated_game_state",
        "source_sha256": fused["source_sha256"],
        "source_interval_s": fused["source_interval_s"],
        "fused_events_sha256": digest(args.fused_events),
        "travel_only_sha256": digest(args.travel_only),
        "counter_audit_sha256": digest(args.counter_audit),
        "ledger_code_sha256": digest(ROOT / "prototype/throw_event_ledger.py"),
        "runner_sha256": digest(Path(__file__)),
        "candidate_count": len(ledger["events"]),
        "origin_view_candidate_count": sum(row["evidence_class"] ==
                                           "origin_view_candidate" for row in ledger["events"]),
        "travel_only_candidate_count": sum(row["evidence_class"] ==
                                            "travel_only_counter_candidate"
                                            for row in ledger["events"]),
        "counter_backed_count": sum(row["counter_id"] is not None
                                    for row in ledger["events"]),
        **ledger,
        "limitations": [
            "Candidate count is not throw count; visual-only events can be false or duplicate physical events.",
            "Broadcast remaining-stone counters are partial observations, not a settled board state.",
            "Release windows are broad; the physical stone identity and trajectory are not reconstructed.",
            "This exposed development source does not establish precision, recall or F1.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"candidates": result["candidate_count"],
                      "counter_backed": result["counter_backed_count"],
                      "counter_without_candidate": len(
                          result["counter_updates_without_candidate"])}))


if __name__ == "__main__":
    main()
