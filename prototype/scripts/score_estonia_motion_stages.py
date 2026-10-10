"""Score frozen and postscore Estonia motion stages against exposed coarse windows."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from throw_event_benchmark import evaluate_events  # noqa: E402

PATH_STATUS = "provisional_unique_far_entry_motion_path"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "candidates",
        "frozen_screen",
        "hold",
        "gaps",
        "dedup",
        "postscore_screen",
        "reference",
        "output",
    ):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Stage score artifact already exists")
    paths = {
        name: getattr(args, name)
        for name in (
            "candidates",
            "frozen_screen",
            "hold",
            "gaps",
            "dedup",
            "postscore_screen",
            "reference",
        )
    }
    data = {name: json.loads(path.read_text()) for name, path in paths.items()}
    candidates = data["candidates"]
    reference = data["reference"]
    if candidates["source_id"] != reference["source_id"] or (
        candidates["source_sha256"] != reference["source_sha256"]
    ):
        parser.error("Candidate and reference source differ")
    candidate_ids = [event["id"] for event in candidates["events"]]
    if len(set(candidate_ids)) != len(candidate_ids):
        parser.error("Candidate IDs are not unique")
    for name in ("hold", "gaps"):
        if {row["candidate_id"] for row in data[name]["rows"]} != set(candidate_ids):
            parser.error(name + " candidate IDs differ")
    for name in ("frozen_screen", "dedup", "postscore_screen"):
        artifact = data[name]
        if artifact["source_id"] != candidates["source_id"] or (
            artifact["source_sha256"] != candidates["source_sha256"]
        ):
            parser.error(name + " source differs")

    def selected_events(name):
        accepted = {
            row["candidate_id"]
            for row in data[name]["rows"]
            if row["selection"]["status"] == PATH_STATUS
        }
        return [event for event in candidates["events"] if event["id"] in accepted]

    stage_events = {
        "candidate_baseline_postscore": candidates["events"],
        "frozen_cross_recording_two_cue": data["frozen_screen"]["events"],
        "registration_hold_postscore": selected_events("hold"),
        "bounded_gaps_postscore": selected_events("gaps"),
        "shared_path_dedup_postscore": data["dedup"]["events"],
        "two_cue_after_repairs_postscore": data["postscore_screen"]["events"],
    }
    stages = []
    for name, events in stage_events.items():
        if len({event["id"] for event in events}) != len(events):
            parser.error(name + " has duplicate event IDs")
        stages.append(
            {
                "stage": name,
                "candidate_ids": [event["id"] for event in events],
                "score": evaluate_events(
                    events, reference["events"], reference["source_interval_s"]
                ),
            }
        )
    result = {
        "status": "exposed_estonia_development_stage_comparison",
        "source_id": candidates["source_id"],
        "input_sha256": {name: file_sha256(path) for name, path in paths.items()},
        "scorer_sha256": file_sha256(ROOT / "prototype/throw_event_benchmark.py"),
        "runner_sha256": file_sha256(__file__),
        "stages": stages,
        "limitations": [
            "Only the frozen cross-recording two-cue stage was fixed before the 1080p Estonia transfer.",
            "Registration hold, bounded gaps, and deduplication were built after inspecting Estonia failures.",
            "The candidate set and coarse reference were already exposed and are not independent exhaustive labels.",
            "A match to coarse windows does not establish release-time accuracy, stone identity, or game-state completeness.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    for stage in stages:
        score = stage["score"]
        print(
            stage["stage"],
            len(stage["candidate_ids"]),
            score["true_positives"],
            score["false_positives"],
            score["false_negatives"],
            round(score["f1"], 3),
        )


if __name__ == "__main__":
    main()
