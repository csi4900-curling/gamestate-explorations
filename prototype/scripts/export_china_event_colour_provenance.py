"""Enrich frozen full-China event candidates with explicit colour provenance."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from event_colour_provenance import annotate_event_colours

BASE = ROOT / "validation/curlobserver-learned-probe/china-full-transfer"
FUSED = BASE / "fused-shot-candidates-replay-cap.json"
CAP = BASE / "two-shot-cap.json"
COUNTER = BASE / "counter-shot-alignment-replay-cap.json"
PLAN = BASE / "event-colour-provenance-v1-plan.json"
OUTPUT = BASE / "event-colour-provenance-v1.json"


def digest(path):
    h = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first provenance export")
    plan = json.loads(PLAN.read_text())
    hashes = {name: digest(path) for name, path in
              (("fused", FUSED), ("cap", CAP), ("counter", COUNTER),
               ("provenance_code", ROOT / "prototype/event_colour_provenance.py"),
               ("runner", __file__))}
    if hashes != plan["sha256"]:
        raise ValueError("Frozen provenance plan changed")
    fused = json.loads(FUSED.read_text())
    cap = json.loads(CAP.read_text())
    counter = json.loads(COUNTER.read_text())
    if (hashes["cap"] != fused["two_shot_sha256"] or
            hashes["counter"] != fused["counter_alignment_sha256"]):
        raise ValueError("Fusion artifact dependency fingerprint mismatch")
    source_hash = fused["source_sha256"]
    if source_hash != cap["source_sha256"] or source_hash != counter["source_sha256"]:
        raise ValueError("Source fingerprint mismatch")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash == reserved["source_sha256"]:
        raise ValueError("Reserved independent source selected")
    events = annotate_event_colours(fused["events"], cap["decisions"],
                                    counter["rows"])
    if [{key: value for key, value in row.items() if key != "colour_provenance"}
            for row in events] != fused["events"]:
        raise ValueError("Colour enrichment modified frozen event fields")
    counts = dict(sorted(Counter(row["colour_provenance"]["basis"]
                                 for row in events).items()))
    output = {
        "status": "source_linked_full_china_event_colour_provenance_not_physical_event_score",
        "source_sha256": source_hash,
        "sha256": hashes,
        "plan_sha256": digest(PLAN),
        "event_count": len(events),
        "basis_counts": counts,
        "events": events,
        "limitations": [
            "Event identities, candidate windows, colours and source evidence are copied from frozen inputs.",
            "A linked broadcast counter is delayed proxy evidence, not a direct visual stone identification.",
            "Ambiguous visual red/yellow motion remains ambiguous even when a counter supplies a colour.",
            "This export does not establish physical throw precision, recall or simulation readiness.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(len(events), counts)


if __name__ == "__main__":
    main()
