"""Merge four complete new-model score shards without dropping proposals."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from right_visual_cue_pair import visual_cue_pair, group_visual_priority

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
SCORER = ROOT / "prototype/scripts/score_latvia_full_right_source_diverse_patch.py"
SHARD_DIR = LAT / "full-right-source-diverse-patch-shards"
OUT = LAT / "full-right-all-proposal-source-diverse-patch-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Combined score already exists")
    queue, context, old = (json.loads(path.read_text()) for path in (
        QUEUE, CONTEXT, OLD))
    training, selection, reviewed = (json.loads(path.read_text()) for path in (
        TRAINING, SELECTION, REVIEWED))
    video_hash = digest(VIDEO)
    if (queue["source_video_sha256"] != video_hash or
            context["input_sha256"]["queue"] != digest(QUEUE) or
            old["input_sha256"]["queue"] != digest(QUEUE) or
            training["selection_sha256"] != digest(SELECTION) or
            training["model_sha256"] != digest(MODEL) or
            reviewed["input_sha256"]["new_model"] != digest(MODEL) or
            any(source["video_sha256"] == video_hash or
                "latvia" in source["video"] for source in selection["sources"])):
        raise ValueError("Source/model lineage differs")
    shards = []
    for index in range(4):
        path = SHARD_DIR / f"part-{index}.json"
        shard = json.loads(path.read_text())
        start, stop = index * 84, (index + 1) * 84
        if (shard["source_video_sha256"] != video_hash or
                shard["queue_sha256"] != digest(QUEUE) or
                shard["context_sha256"] != digest(CONTEXT) or
                shard["old_scores_sha256"] != digest(OLD) or
                shard["new_model_sha256"] != digest(MODEL) or
                shard["reviewed_transfer_sha256"] != digest(REVIEWED) or
                shard["runner_sha256"] != digest(SCORER) or
                shard["shard_index"] != index or
                shard["start_index"] != start or
                shard["stop_index"] != stop or
                len(shard["rows"]) != stop - start):
            raise ValueError(f"Incomplete or inconsistent shard: {index}")
        shards.append((path, shard))
    rows = [row for _, shard in shards for row in shard["rows"]]
    if (len(rows) != queue["proposal_count"] or
            [row["proposal_id"] for row in rows] != [
                row["proposal_id"] for row in context["proposals"]] or
            len({row["proposal_id"] for row in rows}) != len(rows)):
        raise ValueError("Combined proposal inventory differs from queue")
    reviewed_rows = {row["proposal_id"]: row for row in reviewed["rows"]}
    for row in rows:
        prior = reviewed_rows.get(row["proposal_id"])
        if prior is not None and (row["sample_patch_scores"] != prior[
                "new_model_samples"] or row["new_model_any_positive_patch"]
                != prior["new_model_any_positive"]):
            raise ValueError(f"Reviewed score changed: {row['proposal_id']}")
        if row["new_visual_cue_pair_review_tier"] != visual_cue_pair(
                row["context_tier"], row["new_model_any_positive_patch"]):
            raise ValueError("Visual cue tier changed")
    by_id = {row["proposal_id"]: row for row in rows}
    groups = []
    for group in queue["review_groups"]:
        tiers = [by_id[pid]["new_visual_cue_pair_review_tier"]
                 for pid in group["proposal_ids"]]
        groups.append({"review_group_id": group["group_id"],
                       "proposal_ids": group["proposal_ids"],
                       "new_visual_cue_group_priority": group_visual_priority(tiers),
                       "physical_event_verified": False})
    patch_counts = Counter((row["old_model_any_positive_patch"],
                            row["new_model_any_positive_patch"]) for row in rows)
    tier_counts = Counter(row["new_visual_cue_pair_review_tier"] for row in rows)
    group_counts = Counter(group["new_visual_cue_group_priority"]
                           for group in groups)
    result = {
        "status": "full_match_new_patch_visual_review_not_event_filter",
        "source_video_sha256": video_hash,
        "input_sha256": {"queue": digest(QUEUE), "full_context": digest(CONTEXT),
                         "old_full_model_scores": digest(OLD),
                         "training_selection": digest(SELECTION),
                         "training_results": digest(TRAINING),
                         "new_model": digest(MODEL),
                         "reviewed_new_model_transfer": digest(REVIEWED),
                         **{f"score_shard_{index}": digest(path)
                            for index, (path, _) in enumerate(shards)}},
        "score_runner_sha256": digest(SCORER),
        "cue_pair_code_sha256": digest(ROOT / "prototype/right_visual_cue_pair.py"),
        "runner_sha256": digest(Path(__file__)),
        "proposal_count": len(rows),
        "reviewed_score_reproduction_count": len(reviewed_rows),
        "group_count": len(groups),
        "new_patch_positive_proposal_count": sum(row[
            "new_model_any_positive_patch"] for row in rows),
        "old_to_new_patch_counts": {f"old_{int(old)}_new_{int(new)}": patch_counts[
            old, new] for old in (False, True) for new in (False, True)},
        "new_proposal_visual_tier_counts": dict(tier_counts),
        "new_group_visual_priority_counts": dict(group_counts),
        "proposals": rows,
        "review_groups": groups,
        "limitations": [
            "All 336 proposals remain present; patch or visual tier positivity is not a physical throw decision.",
            "The 53 reviewed prefixes were selected after proposal inspection; 283 proposal prefixes lack source-pixel labels.",
            "The new model was fitted without Latvia frames, but its design followed known Latvia development failures.",
            "A stone-like patch may be handled stone, duplicate track or spliced identity; full-match event F1 and game state remain unverified.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"proposals": len(rows), "new_patch_positive": result[
        "new_patch_positive_proposal_count"], "old_to_new": result[
            "old_to_new_patch_counts"], "group_priorities": dict(group_counts)}))


if __name__ == "__main__":
    main()
