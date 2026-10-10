"""Form source-only event candidates from frozen origin and transit evidence."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from origin_receiver_pairing import pair_origin_receiver

BASE = ROOT / "validation/curlobserver-learned-probe"
VISUAL = BASE / "cap-patch-crossmatch-v1/norway-end4-short-transit-first.json"
ORIGINS = BASE / "canada-norway-full-transfer/shot-origin.json"
FROZEN_PAIR = BASE / "cap-patch-crossmatch-v1/norway-end3-origin-receiver-pairs.json"
OUTPUT = BASE / "cap-patch-crossmatch-v1/norway-end4-origin-receiver-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first end-4 pairing result")
    visual, origin = (json.loads(path.read_text()) for path in (VISUAL, ORIGINS))
    frozen = json.loads(FROZEN_PAIR.read_text())
    if frozen["pairing_code_sha256"] != digest(ROOT / "prototype/origin_receiver_pairing.py"):
        raise ValueError("Pairing rule changed after the end-3 diagnostic")
    if frozen["frozen_origin_sha256"] != digest(ORIGINS):
        raise ValueError("Frozen origin decisions changed after end three")
    if visual["source_sha256"] != origin["source_sha256"]:
        raise ValueError("Source mismatch")
    by_id = {row["shot_id"]: row for row in origin["rows"]}
    if not all(
        row["shot_id"] in by_id and row["interval_s"] == by_id[row["shot_id"]]["interval_s"]
        for row in visual["rows"]
    ):
        raise ValueError("Origin and transit camera shots differ")
    events = pair_origin_receiver(visual["rows"], by_id)
    result = {
        "status": "source_only_first_end4_origin_receiver_event_candidates",
        "source_sha256": visual["source_sha256"],
        "visual_sha256": digest(VISUAL),
        "frozen_origin_sha256": digest(ORIGINS),
        "end3_pairing_diagnostic_sha256": digest(FROZEN_PAIR),
        "pairing_code_sha256": digest(ROOT / "prototype/origin_receiver_pairing.py"),
        "runner_sha256": digest(Path(__file__)),
        "end": 4,
        "camera_shot_count": len(visual["rows"]),
        "origin_positive_count": sum(by_id[row["shot_id"]]["predicted"] for row in visual["rows"]),
        "event_candidate_count": len(events),
        "events": events,
        "limitations": [
            "This pairing rule was fixed after exposed end three and before this end-four visual scan finished.",
            "Same-colour adjacent-view evidence is not physical stone identity across a camera cut.",
            "The origin interval is a broad release window, not an exact release time.",
            "No delayed counter, official sequence, or board state enters the pairing function.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        {
            "origins": result["origin_positive_count"],
            "events": len(events),
            "routes": {
                route: sum(e["evidence_route"] == route for e in events)
                for route in sorted({e["evidence_route"] for e in events})
            },
        }
    )


if __name__ == "__main__":
    main()
