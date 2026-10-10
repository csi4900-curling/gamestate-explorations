"""Prepare hash-linked inputs for observing only newly accepted left-bound boards."""

import argparse
from hashlib import sha256
import json
from pathlib import Path


def digest(path):
    value = sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("motion", "integrated_screen", "batch", "candidates",
                 "output_motion", "output_screen"):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    args = parser.parse_args()
    if args.output_motion.exists() or args.output_screen.exists():
        parser.error("Output exists")
    original = json.loads(args.motion.read_text())
    integrated = json.loads(args.integrated_screen.read_text())
    batch = json.loads(args.batch.read_text())
    candidates = json.loads(args.candidates.read_text())
    if (integrated["frozen_motion_sha256"] != digest(args.motion) or
            integrated["bound_batch_sha256"] != digest(args.batch) or
            integrated["candidates_sha256"] != digest(args.candidates) or
            batch["candidates_sha256"] != digest(args.candidates) or
            batch["video_sha256"] != original["high_resolution_source_sha256"]):
        parser.error("Input provenance differs")
    added = integrated["added_candidate_ids"]
    if set(added) != set(batch["changed_selection_ids"]) or len(added) != len(set(added)):
        parser.error("Integrated additions differ from paired-bound changes")
    rows = []
    for row in original["rows"]:
        pid = row["candidate_id"]
        if pid in added:
            paired_path = args.batch.parent / f"{pid.lower()}-paired.json"
            paired = json.loads(paired_path.read_text())
            if (paired["candidate_id"] != pid or
                    paired["source_sha256"] != batch["video_sha256"]):
                parser.error(f"Invalid paired path for {pid}")
            row = dict(row, selection=paired["cases"]["extended"]["selection"])
        rows.append(row)
    if len(rows) != len(original["rows"]):
        raise AssertionError("Motion row coverage changed")
    derived_motion = {**original,
                      "status": "postscore_left_bound_selection_replacements_for_board_observer",
                      "frozen_motion_sha256": digest(args.motion),
                      "bound_batch_sha256": digest(args.batch),
                      "integrated_screen_sha256": digest(args.integrated_screen),
                      "preparation_runner_sha256": digest(Path(__file__)),
                      "replaced_candidate_ids": added,
                      "rows": rows}
    write(args.output_motion, derived_motion)
    accepted = {event["id"]: event for event in integrated["events"]}
    decisions = {row["candidate_id"]: row for row in integrated["decisions"]}
    order = [event["id"] for event in candidates["events"] if event["id"] in added]
    if set(order) != set(added) or any(not decisions[pid]["accepted"] for pid in order):
        raise ValueError("Added events are not accepted in integrated screen")
    screen = {
        "status": "postscore_added_only_left_bound_board_input",
        "source_id": candidates["source_id"],
        "source_sha256": candidates["source_sha256"],
        "source_interval_s": candidates["source_interval_s"],
        "candidates_sha256": digest(args.candidates),
        "motion_sha256": digest(args.output_motion),
        "integrated_screen_sha256": digest(args.integrated_screen),
        "preparation_runner_sha256": digest(Path(__file__)),
        "decisions": [decisions[pid] for pid in order],
        "events": [accepted[pid] for pid in order],
        "limitations": ["Only the 12 added candidate boards are rescanned; all 116 passage candidates still bound quiet tails."],
    }
    write(args.output_screen, screen)
    print(len(order), "added board inputs")


if __name__ == "__main__":
    main()
