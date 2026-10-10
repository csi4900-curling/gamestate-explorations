"""Apply frozen patch evidence alongside context to every right proposal."""

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

BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
VIDEO = BASE / "source-360p.mp4"
QUEUE = BASE / "full-right-variant-review-queue-development.json"
CONTEXT = BASE / "full-right-all-proposal-context-review-development.json"
REVIEWED = BASE / "full-right-reviewed-frozen-sideview-patch-transfer-development.json"
MODEL = ROOT / "validation/curlobserver-learned-probe/sideview-patch-transfer-v1/model.npz"
SCANS = {
    "one_second_greedy": BASE / "full-right-area-first-transfer.json",
    "two_second_greedy": BASE / "full-right-area-gap2-development.json",
    "two_second_global": BASE / "full-right-global-area-development.json",
    "two_second_global_later": BASE / "full-right-global-multi-episode-development.json",
}
OUT = BASE / "full-right-all-proposal-visual-cue-pair-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    queue = json.loads(QUEUE.read_text())
    context = json.loads(CONTEXT.read_text())
    reviewed = json.loads(REVIEWED.read_text())
    scans = {name: json.loads(path.read_text()) for name, path in SCANS.items()}
    video_hash = digest(VIDEO)
    if (queue["source_video_sha256"] != video_hash or
            context["input_sha256"]["queue"] != digest(QUEUE) or
            reviewed["input_sha256"]["queue"] != digest(QUEUE) or
            reviewed["input_sha256"]["model"] != digest(MODEL) or
            any(queue["input_sha256"][name] != digest(path) for name, path
                   in SCANS.items())):
        raise ValueError("Source/score/model lineage mismatch")
    model = load_model(MODEL)
    if float(model["threshold"]) != 0:
        raise ValueError("Frozen patch threshold changed")
    proposal_rows = {}
    raw_tracks = {}
    for name, scan in scans.items():
        entries = (scan["later_review_proposals"] if name.endswith("_later")
                   else scan["directional_review_proposals"])
        for row in entries:
            pid = (f"{name}:{row['raw_track_id']}:"
                   f"{row.get('episode_index_within_raw_track', 1)}")
            proposal_rows[pid] = row
        if "raw_tracks" in scan:
            raw_tracks[name] = {r["track_id"]: r for r in scan["raw_tracks"]}
    raw_tracks["two_second_global_later"] = raw_tracks["two_second_global"]
    if (len(proposal_rows) != queue["proposal_count"] or
            {r["proposal_id"] for r in context["proposals"]} !=
            set(proposal_rows)):
        raise ValueError("Full proposal inventory mismatch")
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not capture.isOpened() or fps <= 0:
        raise ValueError("Source unreadable")
    rows = []
    try:
        for item in context["proposals"]:
            pid = item["proposal_id"]
            proposal = proposal_rows[pid]
            variant, track, _ = pid.split(":")
            points = proposal["observed_prefix_points"]
            if len(points) < 3:
                points = raw_tracks[variant][track]["points"]
            by_time = {point["time_s"]: point for point in points}
            if not all(time in by_time for time in item["sample_times_s"]):
                raise ValueError(f"Context sample absent from track: {pid}")
            samples = []
            for time in item["sample_times_s"]:
                capture.set(cv2.CAP_PROP_POS_FRAMES, round(time * fps))
                ok, frame = capture.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise ValueError(f"Source decode failed: {pid}")
                scored = score_candidates(
                    frame, [{"bbox": by_time[time]["bbox"]}], model)[0]
                samples.append({"time_s": time,
                                "patch_score": round(scored["patch_score"], 6),
                                "patch_accepted": scored["patch_accepted"]})
            patch_positive = any(sample["patch_accepted"] for sample in samples)
            tier = visual_cue_pair(item["frozen_paired_context_tier"],
                                   patch_positive)
            rows.append({
                "proposal_id": pid,
                "review_group_id": item["review_group_id"],
                "context_tier": item["frozen_paired_context_tier"],
                "sample_patch_scores": samples,
                "any_positive_patch": patch_positive,
                "visual_cue_pair_review_tier": tier,
                "physical_throw_verified": False,
                "simulation_ready": False,
            })
    finally:
        capture.release()
    prior = {row["proposal_id"]: row for row in reviewed["rows"]}
    for row in rows:
        previous = prior.get(row["proposal_id"])
        if previous is not None and (row["sample_patch_scores"] != previous[
                "sample_scores"] or row["any_positive_patch"] != previous[
                    "any_positive_patch"]):
            raise ValueError(f"Reviewed patch score changed: {row['proposal_id']}")
    by_id = {row["proposal_id"]: row for row in rows}
    groups = []
    for group in queue["review_groups"]:
        tiers = [by_id[pid]["visual_cue_pair_review_tier"]
                 for pid in group["proposal_ids"]]
        groups.append({"review_group_id": group["group_id"],
                       "proposal_ids": group["proposal_ids"],
                       "visual_cue_group_priority": group_visual_priority(tiers),
                       "physical_event_verified": False})
    tier_counts = Counter(row["visual_cue_pair_review_tier"] for row in rows)
    group_counts = Counter(row["visual_cue_group_priority"] for row in groups)
    reviewed_counts = Counter((prior[row["proposal_id"]]["source_pixel_class"],
                               row["visual_cue_pair_review_tier"])
                              for row in rows if row["proposal_id"] in prior)
    result = {
        "status": "full_match_frozen_visual_cue_pair_review_not_event_filter",
        "source_video_sha256": video_hash,
        "input_sha256": {"queue": digest(QUEUE), "full_context": digest(CONTEXT),
                         "reviewed_patch_transfer": digest(REVIEWED),
                         "model": digest(MODEL),
                         **{name: digest(path) for name, path in SCANS.items()}},
        "feature_code_sha256": digest(ROOT / "prototype/stone_patch_detector.py"),
        "patch_scorer_code_sha256": digest(ROOT / "prototype/cap_patch_verifier.py"),
        "cue_pair_code_sha256": digest(ROOT / "prototype/right_visual_cue_pair.py"),
        "runner_sha256": digest(Path(__file__)),
        "proposal_count": len(rows),
        "group_count": len(groups),
        "reviewed_patch_score_reproduction_count": len(prior),
        "proposal_review_tier_counts": dict(tier_counts),
        "group_review_priority_counts": dict(group_counts),
        "reviewed_source_class_by_tier": {
            cls: {tier: reviewed_counts[cls, tier] for tier in sorted(tier_counts)}
            for cls in sorted({key[0] for key in reviewed_counts})},
        "proposals": rows,
        "review_groups": groups,
        "limitations": [
            "All 336 proposals are retained; visual cue tiers only organize review and cannot confirm or reject physical throws.",
            "The 53 source-pixel classes are selected, correlated, postproposal development evidence, not independent event truth.",
            "A positive patch may be a handled stone or person/equipment; negative patch and cluttered context can miss stone pixels.",
            "No physical-event precision, recall, F1, complete board or simulation-ready state is inferred.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"proposals": len(rows), "groups": len(groups),
                      "proposal_tiers": dict(tier_counts),
                      "group_priorities": dict(group_counts)}))


if __name__ == "__main__":
    main()
