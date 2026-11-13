"""Preserve raw support around every exposed 2022 broadcast counter update."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from counter_sample_support import local_counter_support

INPUTS = {
    "PREL000101": ROOT
    / "validation/curlobserver-learned-probe/swiss-full-transfer/counter-audit.json",
    "PREL000102": ROOT
    / "validation/throw-event-benchmark/layout-router/full-china22-counter-audit.json",
    "PREL000103": ROOT
    / "validation/curlobserver-learned-probe/slovakia-full-transfer/counter-audit.json",
    "CAN-NOR-2022": ROOT
    / "validation/curlobserver-learned-probe/canada-norway-full-transfer/counter-audit.json",
}
OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-counter-sample-support-development.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def build():
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    games = []
    for code, path in INPUTS.items():
        audit = json.loads(path.read_text())
        if audit["source_sha256"] == reserved["source_sha256"]:
            raise ValueError("Reserved source cannot enter development audit")
        rows = [
            local_counter_support(event, audit["counter_samples"])
            for event in audit["counter_events"]
        ]
        scored = [
            row
            for row in rows
            if row["before"]["expected_fraction"] is not None
            and row["after"]["expected_fraction"] is not None
        ]
        games.append(
            {
                "recording_code": code,
                "source_sha256": audit["source_sha256"],
                "raw_counter_audit_sha256": digest(path),
                "raw_counter_event_count": len(rows),
                "both_contexts_visible_count": len(scored),
                "both_expected_fraction_at_least_0_75_count": sum(
                    row["before"]["expected_fraction"] >= 0.75
                    and row["after"]["expected_fraction"] >= 0.75
                    for row in scored
                ),
                "both_expected_fraction_at_least_0_5_count": sum(
                    row["before"]["expected_fraction"] >= 0.5
                    and row["after"]["expected_fraction"] >= 0.5
                    for row in scored
                ),
                "rows": rows,
            }
        )
    return {
        "status": "development_raw_counter_support_not_event_quality_or_f1",
        "rule": "For every raw emitted counter event, retain exact before-state support in [update-12s, update-2s] and after-state support in [update+2s, update+12s], using visible one-second readings only. No threshold changes event acceptance.",
        "code_sha256": digest(ROOT / "prototype/counter_sample_support.py"),
        "runner_sha256": digest(Path(__file__)),
        "games": games,
        "limitations": [
            "One-second overlay reads often alternate because a coloured icon is intermittently missed; low exact-state support is not equivalent to a false physical throw.",
            "The China raw audit has 119 emitted counters, while a later replay has a different event count; IDs must not be joined across versions without an explicit mapping.",
            "This describes the counter reader, not release time or delivered-stone identity.",
            "No event ledger, counter extraction rule, or physical throw F1 changes.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists():
        if OUTPUT.read_text() != payload:
            raise SystemExit("Existing support audit differs from inputs or code")
        print(f"Verified {OUTPUT}")
    else:
        OUTPUT.write_text(payload)
        print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
