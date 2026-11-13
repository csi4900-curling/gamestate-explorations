"""Export existing China events with explicit camera and simulation limits."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from event_grounding_envelope import ground_event_candidates

BASE = ROOT / "validation/curlobserver-learned-probe/china-full-transfer"
EVENTS = BASE / "event-colour-provenance-v1.json"
OVERLAP = BASE / "possible-edit-event-overlap-postscan.json"
TEMPORAL = BASE / "possible-edit-temporal-v1.json"
PLAN = BASE / "event-grounding-envelope-v1-plan.json"
OUTPUT = BASE / "event-grounding-envelope-v1.json"


def digest(path):
    h = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first grounding envelope")
    plan = json.loads(PLAN.read_text())
    hashes = {
        name: digest(path)
        for name, path in (
            ("events", EVENTS),
            ("possible_edit_overlap", OVERLAP),
            ("temporal_edit_tier", TEMPORAL),
            ("grounding_code", ROOT / "prototype/event_grounding_envelope.py"),
            ("runner", __file__),
        )
    }
    if hashes != plan["sha256"]:
        raise ValueError("Frozen grounding plan changed")
    events = json.loads(EVENTS.read_text())
    overlap = json.loads(OVERLAP.read_text())
    temporal = json.loads(TEMPORAL.read_text())
    if len(events["events"]) != plan["expected_event_count"]:
        raise ValueError("Frozen event count changed")
    source_hash = events["source_sha256"]
    if source_hash != overlap["source_sha256"] or source_hash != temporal["source_sha256"]:
        raise ValueError("Source fingerprint mismatch")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash == reserved["source_sha256"]:
        raise ValueError("Reserved independent source selected")
    grounded = ground_event_candidates(events["events"], overlap["rows"], temporal["rows"])
    if [
        {
            key: value
            for key, value in row.items()
            if key not in ("camera_boundary_evidence", "simulation_handoff")
        }
        for row in grounded
    ] != events["events"]:
        raise ValueError("Grounding envelope modified frozen event fields")
    continuity_counts = dict(
        sorted(
            Counter(
                row["camera_boundary_evidence"]["continuity_status"] for row in grounded
            ).items()
        )
    )
    output = {
        "status": "source_scoped_china_event_grounding_envelope_not_simulation_ready",
        "source_sha256": source_hash,
        "sha256": hashes,
        "plan_sha256": digest(PLAN),
        "event_count": len(grounded),
        "camera_continuity_counts": continuity_counts,
        "colour_basis_counts": events["basis_counts"],
        "events": grounded,
        "limitations": [
            "No event candidate, delivery window or resolved colour was changed.",
            "Possible edits and cap-track crossings are unverified evidence, not confirmed identity breaks.",
            "Absence of a proposed edit does not prove continuous stone identity.",
            "No exact release, continuous physical trajectory, settled complete board or simulation-ready state is established.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(len(grounded), continuity_counts)


if __name__ == "__main__":
    main()
