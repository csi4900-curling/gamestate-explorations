"""Score every Latvia right proposal with the non-Latvia-trained patch model."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cap_patch_verifier import score_candidates
from right_visual_cue_pair import visual_cue_pair, group_visual_priority
from stone_patch_detector import load_model

BASE = ROOT / "validation/throw-event-benchmark"
LAT = BASE / "canada-latvia-2024"
VIDEO = LAT / "source-360p.mp4"
QUEUE = LAT / "full-right-variant-review-queue-development.json"
CONTEXT = LAT / "full-right-all-proposal-context-review-development.json"
OLD = LAT / "full-right-all-proposal-visual-cue-pair-development.json"
TRAINING = BASE / "right-sideview-source-diverse-development-v1/training-results.json"
SELECTION = TRAINING.parent / "selection.json"
MODEL = TRAINING.parent / "model.npz"
REVIEWED = TRAINING.parent / "latvia-fixed-source-review-transfer.json"
SCANS = {
    "one_second_greedy": LAT / "full-right-area-first-transfer.json",
    "two_second_greedy": LAT / "full-right-area-gap2-development.json",
    "two_second_global": LAT / "full-right-global-area-development.json",
    "two_second_global_later": LAT / "full-right-global-multi-episode-development.json",
}
OUT = LAT / "full-right-all-proposal-source-diverse-patch-development.json"
SHARD_DIR = LAT / "full-right-source-diverse-patch-shards"
SHARD_COUNT = 4


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shard-index", type=int, choices=range(SHARD_COUNT))
    args = parser.parse_args()
    target = SHARD_DIR / f"part-{args.shard_index}.json" if args.shard_index is not None else OUT
    if target.exists():
        raise ValueError("Target score artifact already exists")
    queue, context, old = (json.loads(p.read_text()) for p in (QUEUE, CONTEXT, OLD))
    training, selection, reviewed = (
        json.loads(p.read_text()) for p in (TRAINING, SELECTION, REVIEWED)
    )
    scans = {name: json.loads(path.read_text()) for name, path in SCANS.items()}
    source_hash = digest(VIDEO)
    if (
        queue["source_video_sha256"] != source_hash
        or context["input_sha256"]["queue"] != digest(QUEUE)
        or old["input_sha256"]["queue"] != digest(QUEUE)
        or training["selection_sha256"] != digest(SELECTION)
        or training["model_sha256"] != digest(MODEL)
        or reviewed["input_sha256"]["new_model"] != digest(MODEL)
        or any(
            src["video_sha256"] == source_hash or "latvia" in src["video"]
            for src in selection["sources"]
        )
        or any(
            queue["input_sha256"][name] != digest(path) or scan["source_sha256"] != source_hash
            for (name, path), scan in zip(SCANS.items(), scans.values())
        )
    ):
        raise ValueError("Source, model or reviewed-result lineage differs")
    model = load_model(MODEL)
    if float(model["threshold"]) != 0:
        raise ValueError("Frozen patch threshold changed")
    proposal_rows = {}
    raw_tracks = {}
    for name, scan in scans.items():
        entries = (
            scan["later_review_proposals"]
            if name.endswith("_later")
            else scan["directional_review_proposals"]
        )
        for row in entries:
            pid = f"{name}:{row['raw_track_id']}:{row.get('episode_index_within_raw_track', 1)}"
            if pid in proposal_rows:
                raise ValueError("Duplicate source proposal")
            proposal_rows[pid] = row
        if "raw_tracks" in scan:
            raw_tracks[name] = {r["track_id"]: r for r in scan["raw_tracks"]}
    raw_tracks["two_second_global_later"] = raw_tracks["two_second_global"]
    if len(proposal_rows) != queue["proposal_count"] or set(proposal_rows) != {
        r["proposal_id"] for r in context["proposals"]
    }:
        raise ValueError("Queue and context proposal identities differ")
    old_rows = {r["proposal_id"]: r for r in old["proposals"]}
    reviewed_rows = {r["proposal_id"]: r for r in reviewed["rows"]}
    if len(old_rows) != len(proposal_rows) or len(reviewed_rows) != 53:
        raise ValueError("Old or reviewed score coverage changed")
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not capture.isOpened() or fps <= 0:
        raise ValueError("Latvia source unreadable")
    start = args.shard_index * 84 if args.shard_index is not None else 0
    stop = (
        min(start + 84, len(context["proposals"]))
        if args.shard_index is not None
        else len(context["proposals"])
    )
    rows = []
    try:
        for item in context["proposals"][start:stop]:
            pid = item["proposal_id"]
            variant, track, _ = pid.split(":")
            proposal = proposal_rows[pid]
            points = proposal["observed_prefix_points"]
            if len(points) < 3:
                points = raw_tracks[variant][track]["points"]
            point_by_time = {point["time_s"]: point for point in points}
            if not all(time in point_by_time for time in item["sample_times_s"]):
                raise ValueError(f"Context sample absent from track: {pid}")
            samples = []
            for time in item["sample_times_s"]:
                capture.set(cv2.CAP_PROP_POS_FRAMES, round(time * fps))
                ok, frame = capture.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise ValueError(f"Source decode failed: {pid}")
                scored = score_candidates(frame, [{"bbox": point_by_time[time]["bbox"]}], model)[0]
                samples.append(
                    {
                        "time_s": time,
                        "patch_score": round(scored["patch_score"], 6),
                        "patch_accepted": scored["patch_accepted"],
                    }
                )
            patch_positive = any(sample["patch_accepted"] for sample in samples)
            previous = reviewed_rows.get(pid)
            if previous is not None and (
                samples != previous["new_model_samples"]
                or patch_positive != previous["new_model_any_positive"]
            ):
                raise ValueError(f"Reviewed new-model score changed: {pid}")
            old_positive = old_rows[pid]["any_positive_patch"]
            rows.append(
                {
                    "proposal_id": pid,
                    "review_group_id": item["review_group_id"],
                    "context_tier": item["frozen_paired_context_tier"],
                    "sample_patch_scores": samples,
                    "old_model_any_positive_patch": old_positive,
                    "new_model_any_positive_patch": patch_positive,
                    "new_visual_cue_pair_review_tier": visual_cue_pair(
                        item["frozen_paired_context_tier"], patch_positive
                    ),
                    "physical_throw_verified": False,
                    "simulation_ready": False,
                }
            )
    finally:
        capture.release()
    if args.shard_index is not None:
        if len(rows) != stop - start:
            raise ValueError("Shard output is incomplete")
        SHARD_DIR.mkdir(parents=True, exist_ok=True)
        shard = {
            "status": "full_right_new_patch_score_shard_not_event_filter",
            "source_video_sha256": source_hash,
            "queue_sha256": digest(QUEUE),
            "context_sha256": digest(CONTEXT),
            "old_scores_sha256": digest(OLD),
            "new_model_sha256": digest(MODEL),
            "reviewed_transfer_sha256": digest(REVIEWED),
            "runner_sha256": digest(Path(__file__)),
            "shard_index": args.shard_index,
            "start_index": start,
            "stop_index": stop,
            "rows": rows,
        }
        target.write_text(json.dumps(shard, indent=2) + "\n")
        print(json.dumps({"shard": args.shard_index, "rows": len(rows)}))
        return
    by_id = {r["proposal_id"]: r for r in rows}
    groups = []
    for group in queue["review_groups"]:
        tiers = [by_id[pid]["new_visual_cue_pair_review_tier"] for pid in group["proposal_ids"]]
        groups.append(
            {
                "review_group_id": group["group_id"],
                "proposal_ids": group["proposal_ids"],
                "new_visual_cue_group_priority": group_visual_priority(tiers),
                "physical_event_verified": False,
            }
        )
    patch_counts = Counter(
        (r["old_model_any_positive_patch"], r["new_model_any_positive_patch"]) for r in rows
    )
    tier_counts = Counter(r["new_visual_cue_pair_review_tier"] for r in rows)
    group_counts = Counter(g["new_visual_cue_group_priority"] for g in groups)
    result = {
        "status": "full_match_new_patch_visual_review_not_event_filter",
        "source_video_sha256": source_hash,
        "input_sha256": {
            "queue": digest(QUEUE),
            "full_context": digest(CONTEXT),
            "old_full_model_scores": digest(OLD),
            "training_selection": digest(SELECTION),
            "training_results": digest(TRAINING),
            "new_model": digest(MODEL),
            "reviewed_new_model_transfer": digest(REVIEWED),
            **{name: digest(path) for name, path in SCANS.items()},
        },
        "feature_code_sha256": digest(ROOT / "prototype/stone_patch_detector.py"),
        "patch_scorer_code_sha256": digest(ROOT / "prototype/cap_patch_verifier.py"),
        "cue_pair_code_sha256": digest(ROOT / "prototype/right_visual_cue_pair.py"),
        "runner_sha256": digest(Path(__file__)),
        "proposal_count": len(rows),
        "reviewed_score_reproduction_count": len(reviewed_rows),
        "group_count": len(groups),
        "new_patch_positive_proposal_count": sum(r["new_model_any_positive_patch"] for r in rows),
        "old_to_new_patch_counts": {
            f"old_{int(old)}_new_{int(new)}": patch_counts[old, new]
            for old in (False, True)
            for new in (False, True)
        },
        "new_proposal_visual_tier_counts": dict(tier_counts),
        "new_group_visual_priority_counts": dict(group_counts),
        "proposals": rows,
        "review_groups": groups,
        "limitations": [
            "All 336 proposals remain present; patch or visual tier positivity is not a physical throw decision.",
            "The 53 reviewed prefixes were selected after proposal inspection; 283 proposal prefixes lack source-pixel labels.",
            "The new model was fitted without Latvia frames, but its architecture and source selection followed known Latvia development failures.",
            "A stone-like patch may be a handled stone, duplicate track or spliced identity; full-match event F1 and game state remain unverified.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "proposals": len(rows),
                "new_patch_positive": result["new_patch_positive_proposal_count"],
                "old_to_new": result["old_to_new_patch_counts"],
                "group_priorities": dict(group_counts),
            }
        )
    )


if __name__ == "__main__":
    main()
