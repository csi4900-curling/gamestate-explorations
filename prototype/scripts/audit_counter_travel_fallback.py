"""Audit counter-backed travel-only candidates with no claimed release shot."""

import argparse
import json
from pathlib import Path

from prototype.counter_travel_fallback import travel_only_candidates


ROOT = Path(__file__).resolve().parents[2]


def sha256(path):
    from hashlib import sha256 as hash_bytes

    return hash_bytes(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origins", required=True, type=Path)
    parser.add_argument("--counter-alignment", required=True, type=Path)
    parser.add_argument("--cap-motion", required=True, type=Path)
    parser.add_argument("--learned-motion", required=True, type=Path)
    parser.add_argument("--fused-events", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first travel-only audit")
    origins = json.loads(args.origins.read_text())
    counter = json.loads(args.counter_alignment.read_text())
    cap = json.loads(args.cap_motion.read_text())
    learned = json.loads(args.learned_motion.read_text())
    fused = json.loads(args.fused_events.read_text())
    sources = (counter, cap, learned, fused)
    if any(
        row["source_sha256"] != origins["source_sha256"]
        or row["source_interval_s"] != origins["source_interval_s"]
        for row in sources
    ):
        parser.error("Source or interval fingerprints differ")
    if (
        counter["shot_score_sha256"] != sha256(args.origins)
        or (fused["origins_sha256"] != sha256(args.origins))
        or (fused["counter_alignment_sha256"] != sha256(args.counter_alignment))
    ):
        parser.error("Derived evidence does not match supplied origins/counter")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if origins["source_sha256"] == reserved["source_sha256"]:
        parser.error("Reserved independent source cannot be used for development")
    rows = travel_only_candidates(
        counter["rows"], origins["rows"], cap["shots"], learned["shots"], fused["events"]
    )
    candidates = [row for row in rows if row["travel_shot_id"]]
    result = {
        "status": "postscore_development_counter_backed_travel_only_candidates",
        "source_sha256": origins["source_sha256"],
        "source_interval_s": origins["source_interval_s"],
        "origins_sha256": sha256(args.origins),
        "counter_alignment_sha256": sha256(args.counter_alignment),
        "cap_motion_sha256": sha256(args.cap_motion),
        "learned_motion_sha256": sha256(args.learned_motion),
        "fused_events_sha256": sha256(args.fused_events),
        "fallback_code_sha256": sha256(ROOT / "prototype/counter_travel_fallback.py"),
        "runner_sha256": sha256(Path(__file__)),
        "candidate_count": len(candidates),
        "rows": rows,
        "limitations": [
            "The source broadcast may omit the physical release; the release window is broad.",
            "Same-colour cap and learned tracks can depict a displaced old stone.",
            "Counter updates can be delayed or missing; these are candidate events, not F1 truth.",
            "This fallback was specified after full-source development misses and is not independent validation.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "travel_only_candidates": len(candidates),
                "unassociated_counter_changes": sum(
                    row["shot_id"] is None for row in counter["rows"]
                ),
            }
        )
    )


if __name__ == "__main__":
    main()
