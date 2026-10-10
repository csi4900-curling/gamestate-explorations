"""Replay frozen screen and dedup with only newly unique left-bound paths.

This is an exposed-match development sequence, not independently verified
throw truth. The original frozen decisions are reproduced before replacement.
"""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from candidate_motion_rescue_screen import screen_rescue_candidate  # noqa: E402
from motion_path_dedup import deduplicate_motion_paths  # noqa: E402


def digest(path):
    value = sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def replay(events, motions, patches):
    ids = [event["id"] for event in events]
    if (len(ids) != len(set(ids)) or set(ids) != set(motions) or
            set(ids) != set(patches)):
        raise ValueError("Candidate, motion and patch IDs differ")
    decisions = [screen_rescue_candidate(motions[pid], patches[pid]) for pid in ids]
    by_id = {row["candidate_id"]: row for row in decisions}
    eligible = []
    for pid in ids:
        row = dict(motions[pid])
        if not by_id[pid]["accepted"]:
            row["selection"] = {"path": []}
        eligible.append(row)
    dedup = deduplicate_motion_paths(events, eligible)
    for row in dedup["decisions"]:
        pid = row["candidate_id"]
        if by_id[pid]["accepted"] and row["status"] != "primary_motion_path":
            by_id[pid].update(status="duplicate_shared_timed_motion_path",
                              accepted=False,
                              primary_candidate_id=row["primary_candidate_id"])
    return decisions, dedup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("candidates", "motion", "patch", "screen", "batch", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    candidates = json.loads(args.candidates.read_text())
    motion = json.loads(args.motion.read_text())
    patch = json.loads(args.patch.read_text())
    screen = json.loads(args.screen.read_text())
    batch = json.loads(args.batch.read_text())
    if (motion["source_motion_sha256"] != patch["source_motion_sha256"] or
            patch["motion_sha256"] != digest(args.motion) or
            screen["motion_sha256"] != digest(args.motion) or
            screen["patch_sha256"] != digest(args.patch) or
            screen["candidates_sha256"] != digest(args.candidates) or
            screen["screen_code_sha256"] != digest(ROOT / "prototype/candidate_motion_rescue_screen.py") or
            screen["dedup_code_sha256"] != digest(ROOT / "prototype/motion_path_dedup.py") or
            batch["candidates_sha256"] != digest(args.candidates) or
            batch["video_sha256"] != patch["video_sha256"]):
        raise ValueError("Input or frozen code hash chain differs")
    events = candidates["events"]
    motions = {row["candidate_id"]: row for row in motion["rows"]}
    patches = {row["candidate_id"]: row for row in patch["rows"]}
    baseline, baseline_dedup = replay(events, motions, patches)
    if (baseline != screen["decisions"] or
            baseline_dedup["pairs"] != screen["shared_timed_path_pairs"] or
            {row["candidate_id"] for row in baseline if row["accepted"]} !=
            {event["id"] for event in screen["events"]}):
        raise ValueError("Could not exactly reproduce frozen full-match screen")
    original_by_id = {row["candidate_id"]: row for row in baseline}
    provenance = []
    model_sha = patch["model_sha256"]
    batch_by_id = {row["candidate_id"]: row for row in batch["rows"]}
    if len(batch_by_id) != len(batch["rows"]):
        raise ValueError("Duplicate candidate in paired-bound manifest")
    frozen_intervals = {}
    for pid in (row["candidate_id"] for row in baseline if row["accepted"]):
        times = [node["source_time_s"] for node in motions[pid]["selection"]["path"]]
        frozen_intervals[pid] = (min(times), max(times))
    for pid in batch["changed_selection_ids"]:
        paired_path = args.batch.parent / f"{pid.lower()}-paired.json"
        patch_path = args.batch.parent / f"{pid.lower()}-extended-patch.json"
        paired = json.loads(paired_path.read_text())
        postscore = json.loads(patch_path.read_text())
        batch_row = batch_by_id[pid]
        if (batch_row["artifact"] != paired_path.name or
                batch_row["artifact_sha256"] != digest(paired_path) or
                batch_row["original_selection"] != "no_supported_far_entry_motion_path" or
                batch_row["extended_selection"] != "provisional_unique_far_entry_motion_path" or
                paired["candidate_id"] != pid or
                paired["candidates_sha256"] != digest(args.candidates) or
                postscore["candidate_id"] != pid or
                postscore["probe_sha256"] != digest(paired_path) or
                postscore["model_sha256"] != model_sha or
                not postscore["decision"]["accepted"] or
                original_by_id[pid]["status"] != "abstain_no_supported_motion_path"):
            raise ValueError(f"Invalid changed-path evidence for {pid}")
        motions[pid] = dict(motions[pid],
                            selection=paired["cases"]["extended"]["selection"])
        patches[pid] = dict(patches[pid], samples=postscore["samples"])
        times = [node["source_time_s"] for node in motions[pid]["selection"]["path"]]
        start, end = min(times), max(times)
        gap_s, closest_id = min((start - other_end if start > other_end else
                                 other_start - end if end < other_start else 0,
                                 other_id)
                                for other_id, (other_start, other_end)
                                in frozen_intervals.items())
        provenance.append({"candidate_id": pid,
                           "paired_sha256": digest(paired_path),
                           "patch_sha256": digest(patch_path),
                           "path_sample_count": len(motions[pid]["selection"]["path"]),
                           "accepted_patch_count": postscore["decision"]["accepted_patch_count"],
                           "closest_frozen_accepted_path_id": closest_id,
                           "closest_frozen_accepted_path_window_gap_s": gap_s})
    decisions, dedup = replay(events, motions, patches)
    accepted = {row["candidate_id"] for row in decisions if row["accepted"]}
    frozen = {event["id"] for event in screen["events"]}
    output = {
        "status": "postscore_integrated_left_bound_replay_not_independent_throw_validation",
        "source_id": candidates["source_id"],
        "source_sha256": candidates["source_sha256"],
        "source_interval_s": candidates["source_interval_s"],
        "candidates_sha256": digest(args.candidates),
        "frozen_motion_sha256": digest(args.motion),
        "frozen_patch_sha256": digest(args.patch),
        "frozen_screen_sha256": digest(args.screen),
        "bound_batch_sha256": digest(args.batch),
        "screen_code_sha256": digest(ROOT / "prototype/candidate_motion_rescue_screen.py"),
        "dedup_code_sha256": digest(ROOT / "prototype/motion_path_dedup.py"),
        "runner_sha256": digest(Path(__file__)),
        "frozen_baseline_exactly_reproduced": True,
        "frozen_accepted_count": len(frozen),
        "development_accepted_count": len(accepted),
        "added_candidate_ids": sorted(accepted - frozen),
        "removed_candidate_ids": sorted(frozen - accepted),
        "changed_path_provenance": provenance,
        "minimum_changed_to_frozen_path_window_gap_s": min(
            row["closest_frozen_accepted_path_window_gap_s"] for row in provenance),
        "shared_timed_path_pairs": dedup["pairs"],
        "new_shared_timed_path_pairs": [pair for pair in dedup["pairs"]
                                       if pair not in baseline_dedup["pairs"]],
        "decision_status_counts": dict(Counter(row["status"] for row in decisions)),
        "decisions": decisions,
        "events": [event for event in events if event["id"] in accepted],
        "limitations": [
            "Replaces only the 12 exposed-match newly unique left paths; unchanged candidates preserve frozen observations.",
            "The fixed dedup catches at least five shared timed path observations, not every form of physical duplicate.",
            "Source-selected three-frame stone review and frozen patch scores are not independent throw-event labels.",
            "This replay does not verify release/settle times, physical stone identity, game state, or event-level precision/recall/F1.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print("frozen", len(frozen), "derived", len(accepted),
          "added", output["added_candidate_ids"],
          "removed", output["removed_candidate_ids"],
          "new dedup pairs", len(output["new_shared_timed_path_pairs"]))


if __name__ == "__main__":
    main()
