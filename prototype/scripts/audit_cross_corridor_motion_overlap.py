"""Find timed receiving paths shared across selected and withheld raw candidates."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from motion_path_dedup import shared_timed_observations  # noqa: E402


def unique(rows, key):
    values = {row[key]: row for row in rows}
    if len(values) != len(rows):
        raise ValueError(f"Duplicate {key}")
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("corridor", "selected_motion", "withheld_motion", "screen"):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Audit already exists")
    corridor = json.loads(args.corridor.read_text())
    selected = json.loads(args.selected_motion.read_text())
    withheld = json.loads(args.withheld_motion.read_text())
    screen = json.loads(args.screen.read_text())
    selected_rows = unique(selected["rows"], "candidate_id")
    withheld_rows = unique(withheld["rows"], "candidate_id")
    decisions = unique(screen["decisions"], "candidate_id")
    if (set(selected_rows) != {row["id"] for row in corridor["events"]} or
            set(withheld_rows) != {row["id"] for row in corridor["withheld_events"]} or
            set(decisions) != set(selected_rows) or
            screen["motion_sha256"] != file_sha256(args.selected_motion) or
            screen["candidates_sha256"] != file_sha256(args.corridor) or
            selected["high_resolution_source_sha256"] !=
            withheld["high_resolution_source_sha256"]):
        parser.error("Source, corridor, motion or screen coverage differs")
    pairs = []
    for first in selected_rows.values():
        path = first["selection"].get("path") or []
        if not path:
            continue
        for second in withheld_rows.values():
            other = second["selection"].get("path") or []
            if not other or first["colour"] != second["colour"] or (
                    first["receiving_view"] != second["receiving_view"]):
                continue
            shared = shared_timed_observations(path, other)
            if shared >= 5:
                pairs.append({
                    "selected_candidate_id": first["candidate_id"],
                    "withheld_candidate_id": second["candidate_id"],
                    "shared_timed_observation_count": shared,
                    "selected_screen_accepted": decisions[first["candidate_id"]]["accepted"],
                    "selected_view": first["receiving_view"],
                    "colour": first["colour"],
                })
    output = {
        "status": "postscore_cross_corridor_path_overlap_not_event_truth",
        "source_id": corridor["source_id"],
        "source_sha256": corridor["source_sha256"],
        "high_resolution_source_sha256": selected["high_resolution_source_sha256"],
        "input_sha256": {name: file_sha256(getattr(args, name)) for name in
                         ("corridor", "selected_motion", "withheld_motion", "screen")},
        "dedup_code_sha256": file_sha256(ROOT / "prototype/motion_path_dedup.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "selected_candidate_count": len(selected_rows),
        "withheld_candidate_count": len(withheld_rows),
        "minimum_shared_timed_observations": 5,
        "position_tolerance_m_conditional": 0.15,
        "pair_count": len(pairs),
        "selected_candidate_count_with_pair": len({p["selected_candidate_id"] for p in pairs}),
        "accepted_selected_candidate_ids_with_pair": sorted({p["selected_candidate_id"]
                                                               for p in pairs if p["selected_screen_accepted"]}),
        "pair_acceptance_counts": dict(Counter("accepted" if p["selected_screen_accepted"]
                                               else "abstained" for p in pairs)),
        "pairs": pairs,
        "limitations": [
            "A shared candidate-local path does not prove a physical stone or false positive.",
            "The fixed corridor's withheld IDs were inspected on this exposed match; this is development evidence.",
            "The threshold uses conditional view-local projected positions, not independently validated metric geometry.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(output["pair_count"], "cross-corridor pairs; accepted IDs",
          output["accepted_selected_candidate_ids_with_pair"])


if __name__ == "__main__":
    main()
