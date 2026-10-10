"""Link unmatched counters to already-emitted visual candidates across cuts."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from prototype.counter_shot_alignment import link_existing_visual_candidates


ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origins", required=True, type=Path)
    parser.add_argument("--alignment", required=True, type=Path)
    parser.add_argument("--cap-motion", required=True, type=Path)
    parser.add_argument("--learned-motion", required=True, type=Path)
    parser.add_argument("--fused-events", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first conflict-link result")
    origins = json.loads(args.origins.read_text())
    alignment = json.loads(args.alignment.read_text())
    cap = json.loads(args.cap_motion.read_text())
    learned = json.loads(args.learned_motion.read_text())
    fused = json.loads(args.fused_events.read_text())
    if any(row["source_sha256"] != origins["source_sha256"] or
           row["source_interval_s"] != origins["source_interval_s"]
           for row in (alignment, cap, learned, fused)):
        parser.error("Evidence source or interval fingerprints differ")
    if alignment["shot_score_sha256"] != digest(args.origins) or (
            fused["origins_sha256"] != digest(args.origins)) or (
            fused["counter_alignment_sha256"] != digest(args.alignment)):
        parser.error("Derived evidence does not match the supplied origins/alignment")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if origins["source_sha256"] == reserved["source_sha256"]:
        parser.error("Reserved independent source cannot be used for development")
    rows = link_existing_visual_candidates(
        alignment["rows"], origins["rows"], fused["events"],
        {"cap": cap["shots"], "learned": learned["shots"]})
    linked = [row for row in rows if row["association_route"] ==
              "existing_visual_candidate_and_following_motion"]
    result = {
        "status": "postscore_development_existing_visual_counter_link",
        "source_sha256": origins["source_sha256"],
        "source_interval_s": origins["source_interval_s"],
        "shot_score_sha256": digest(args.origins),
        "input_alignment_sha256": digest(args.alignment),
        "cap_motion_sha256": digest(args.cap_motion),
        "learned_motion_sha256": digest(args.learned_motion),
        "fused_events_sha256": digest(args.fused_events),
        "link_code_sha256": digest(ROOT / "prototype/counter_shot_alignment.py"),
        "runner_sha256": digest(Path(__file__)),
        "counter_event_count": len(rows),
        "associated_count": sum(row["shot_id"] is not None for row in rows),
        "new_link_count": len(linked),
        "rows": rows,
        "limitations": [
            "Postscore rule selected after visual-only review on exposed full-source footage.",
            "A next-shot motion match does not prove physical stone identity.",
            "Counter/visual colour disagreements must stay explicit; no independent F1 follows.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"associated": result["associated_count"],
                      "counter_events": len(rows), "new_links": len(linked)}))


if __name__ == "__main__":
    main()
