"""Attach the frozen three-way context cue without changing event acceptance."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from track_context_triage import classify_context


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", required=True, type=Path)
    parser.add_argument("--confirmed", required=True, type=Path)
    parser.add_argument("--tracks", required=True, type=Path)
    parser.add_argument("--context", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first triage")
    raw, confirmed, tracks, context = (
        json.loads(path.read_text())
        for path in (args.raw, args.confirmed, args.tracks, args.context)
    )
    if len({row["source_sha256"] for row in (raw, confirmed, tracks, context)}) != 1:
        raise ValueError("Source fingerprints differ")
    if tracks["raw_artifact_sha256"] != digest(args.raw):
        raise ValueError("Track replay differs from raw candidates")
    if context["tracks_artifact_sha256"] != digest(args.tracks):
        raise ValueError("Context diagnostic differs from tracks")
    if confirmed["input_sha256"] != digest(args.raw):
        raise ValueError("Previous confirmation differs from raw candidates")
    by_id = {row["event_id"]: row for row in context["rows"]}
    accepted = {row["id"] for row in confirmed["events"]}
    raw_ids = {row["id"] for row in raw["events"]}
    if len(by_id) != len(raw_ids) or set(by_id) != raw_ids or not accepted <= raw_ids:
        raise ValueError("Raw, context and confirmed candidate IDs disagree")
    rows = []
    for candidate in raw["events"]:
        event_id = candidate["id"]
        diagnostic = by_id[event_id]
        index = (
            diagnostic["context"]["full"]["comovement_index"]
            if diagnostic["status"] == "scored_surrounding_motion"
            else None
        )
        rows.append(
            {
                "candidate_id": event_id,
                "candidate_time_s": candidate["crossing_time_s"],
                "colour_claim": candidate["colour"],
                "previously_auto_accepted": event_id in accepted,
                "comovement_index": index,
                "context_cue": classify_context(index),
                "physical_throw_verified": False,
            }
        )
    summary = {}
    for previous in (True, False):
        group = [row for row in rows if row["previously_auto_accepted"] == previous]
        summary["previously_accepted" if previous else "previously_withheld"] = {
            "total": len(group),
            "cue_counts": {
                cue: sum(row["context_cue"] == cue for row in group)
                for cue in (
                    "isolated_motion_cue",
                    "ambiguous_context",
                    "comoving_context_review",
                    "abstain_insufficient_motion",
                )
            },
        }
    result = {
        "status": "additive_track_context_review_not_revised_event_acceptance",
        "source_sha256": raw["source_sha256"],
        "source_interval_s": raw["source_interval_s"],
        "raw_sha256": digest(args.raw),
        "confirmed_sha256": digest(args.confirmed),
        "track_sha256": digest(args.tracks),
        "context_sha256": digest(args.context),
        "triage_code_sha256": digest(ROOT / "prototype/track_context_triage.py"),
        "runner_sha256": digest(Path(__file__)),
        "thresholds": {"isolated_at_or_below": -0.20, "comoving_at_or_above": 0.20},
        "summary": summary,
        "rows": rows,
        "limitations": [
            "Cue thresholds were selected after inspecting Scotland and are development-only.",
            "Surrounding motion can include a player near a real stone or camera movement.",
            "Previous acceptance is preserved and physical throw identity remains unverified.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
