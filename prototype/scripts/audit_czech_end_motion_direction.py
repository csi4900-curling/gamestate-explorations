"""Describe direction consistency within stable Czech end-marker runs."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/layout-router/czech24-full-camera-motion-v1"
INVENTORY = BASE / "end-conditioned-candidate-inventory.json"
RAW = BASE / "run-02/raw.json"
OUT = BASE / "end-conditioned-motion-direction-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Direction audit exists")
    inventory, raw = (json.loads(p.read_text()) for p in (INVENTORY, RAW))
    if inventory["source_sha256"] != raw["source_sha256"] or inventory["input_sha256"][
        "raw"
    ] != digest(RAW):
        raise ValueError("Inventory and raw source differ")
    by_id = {e["id"]: e for e in raw["events"]}
    rows = []
    for run in inventory["stable_marker_end_rows"]:
        confirmed = run["context_confirmed_candidate_ids"]
        count = Counter(by_id[id]["view_motion"] for id in confirmed)
        if len(count) > 2 or not count:
            raise ValueError("Unexpected direction inventory")
        dominant = count.most_common(1)[0][0]
        exceptions = [id for id in confirmed if by_id[id]["view_motion"] != dominant]
        rows.append(
            {
                "end_marker": run["end_marker"],
                "stable_interval_s": run["stable_marker_hit_interval_s"],
                "context_confirmed_candidate_count": len(confirmed),
                "direction_counts": dict(count),
                "dominant_direction": dominant,
                "opposite_direction_candidate_ids": exceptions,
            }
        )
    OUT.write_text(
        json.dumps(
            {
                "status": "within_marker_direction_development_audit_not_throw_classification",
                "source_sha256": raw["source_sha256"],
                "input_sha256": {"inventory": digest(INVENTORY), "raw": digest(RAW)},
                "runner_sha256": digest(Path(__file__)),
                "rows": rows,
                "limitations": [
                    "Dominance is calculated from context-confirmed candidates, which include false paths and may omit throws.",
                    "The stable broadcast end marker is intermittent and does not define exact physical end boundaries.",
                    "A genuine collision, replay, camera reversal, or other scene motion could contradict the dominant image direction; this is not an automatic event veto.",
                ],
            },
            indent=2,
        )
        + "\n"
    )
    print(
        json.dumps(
            [
                (r["end_marker"], r["direction_counts"], r["opposite_direction_candidate_ids"])
                for r in rows
            ]
        )
    )


if __name__ == "__main__":
    main()
