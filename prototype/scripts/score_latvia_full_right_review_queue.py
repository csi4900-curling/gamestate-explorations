"""Score every Latvia right proposal with frozen visual-context review cues."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from right_context_tier import context_tier
from right_track_ice_context import three_sample_context
from right_track_underpoint_context import three_sample_underpoint

BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
VIDEO = BASE / "source-360p.mp4"
QUEUE = BASE / "full-right-variant-review-queue-development.json"
REVIEWED = BASE / "full-right-reviewed-context-transfer-development.json"
SCANS = {
    "one_second_greedy": BASE / "full-right-area-first-transfer.json",
    "two_second_greedy": BASE / "full-right-area-gap2-development.json",
    "two_second_global": BASE / "full-right-global-area-development.json",
    "two_second_global_later": BASE / "full-right-global-multi-episode-development.json",
}
OUT = BASE / "full-right-all-proposal-context-review-development.json"
THRESHOLD = 0.25


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    queue = json.loads(QUEUE.read_text())
    reviewed = json.loads(REVIEWED.read_text())
    scans = {name: json.loads(path.read_text()) for name, path in SCANS.items()}
    video_hash = digest(VIDEO)
    if queue["source_video_sha256"] != video_hash or any(
        scan["source_sha256"] != video_hash or queue["input_sha256"][name] != digest(SCANS[name])
        for name, scan in scans.items()
    ):
        raise ValueError("Source/scan lineage mismatch")
    if (
        reviewed["input_sha256"]["queue"] != digest(QUEUE)
        or reviewed["frozen_paired_threshold"] != THRESHOLD
    ):
        raise ValueError("Reviewed transfer differs from full-queue rule")
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
    if set(proposal_rows) != {p["proposal_id"] for p in queue["proposals"]}:
        raise ValueError("Queue has missing or extra proposal identities")
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not capture.isOpened() or fps <= 0:
        raise ValueError("Source unreadable")
    rows = []
    try:
        for entry in queue["proposals"]:
            pid = entry["proposal_id"]
            proposal = proposal_rows[pid]
            points = proposal["observed_prefix_points"]
            if len(points) < 3:
                points = raw_tracks[entry["variant"]][entry["raw_track_id"]]["points"]
                sampling_policy = "nearest_three_raw_track_points"
            else:
                sampling_policy = "nearest_three_prefix_points"
            time = proposal["passage"]["time_s"]
            samples = sorted(
                sorted(points, key=lambda p: (abs(p["time_s"] - time), p["time_s"]))[:3],
                key=lambda p: p["time_s"],
            )
            if len(samples) != 3:
                raise ValueError(f"Too few points: {pid}")
            frames = []
            for point in samples:
                capture.set(cv2.CAP_PROP_POS_FRAMES, round(point["time_s"] * fps))
                ok, frame = capture.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise ValueError(f"Source decode failed: {pid}")
                frames.append(frame)
            ring = three_sample_context(frames, samples)
            under = three_sample_underpoint(frames, samples)
            ring_value = ring["median_nonice_ring_fraction"]
            under_value = under["median_underpoint_nonice_fraction"]
            rows.append(
                {
                    "proposal_id": pid,
                    "review_group_id": entry["review_group_id"],
                    "passage_time_s": time,
                    "sample_times_s": [point["time_s"] for point in samples],
                    "sampling_policy": sampling_policy,
                    "median_nonice_ring_fraction": ring_value,
                    "median_underpoint_nonice_fraction": under_value,
                    "frozen_paired_context_tier": context_tier(
                        ring_value, under_value, threshold=THRESHOLD
                    ),
                    "physical_throw_verified": False,
                    "simulation_ready": False,
                }
            )
    finally:
        capture.release()
    reviewed_rows = {row["proposal_id"]: row for row in reviewed["rows"]}
    for row in rows:
        prior = reviewed_rows.get(row["proposal_id"])
        if prior is None:
            continue
        for key in (
            "sample_times_s",
            "median_nonice_ring_fraction",
            "median_underpoint_nonice_fraction",
            "frozen_paired_context_tier",
        ):
            if row[key] != prior[key]:
                raise ValueError(f"Reviewed score changed for {row['proposal_id']}: {key}")
    by_id = {row["proposal_id"]: row for row in rows}
    groups = []
    for group in queue["review_groups"]:
        tiers = [by_id[pid]["frozen_paired_context_tier"] for pid in group["proposal_ids"]]
        if "clear_context_review" in tiers:
            priority = "has_clear_context_proposal"
        elif "context_unavailable_review" in tiers:
            priority = "context_unavailable_or_cluttered_review"
        else:
            priority = "all_proposals_context_cluttered_review"
        groups.append(
            {
                "review_group_id": group["group_id"],
                "proposal_ids": group["proposal_ids"],
                "context_review_priority": priority,
                "physical_event_verified": False,
            }
        )
    counts = Counter(row["frozen_paired_context_tier"] for row in rows)
    group_counts = Counter(row["context_review_priority"] for row in groups)
    result = {
        "status": "full_match_visual_context_review_priorities_not_throw_filter",
        "source_video_sha256": video_hash,
        "input_sha256": {
            "queue": digest(QUEUE),
            "reviewed_transfer": digest(REVIEWED),
            **{name: digest(path) for name, path in SCANS.items()},
        },
        "feature_code_sha256": {
            "ring": digest(ROOT / "prototype/right_track_ice_context.py"),
            "underpoint": digest(ROOT / "prototype/right_track_underpoint_context.py"),
            "paired_tier": digest(ROOT / "prototype/right_context_tier.py"),
        },
        "runner_sha256": digest(Path(__file__)),
        "frozen_paired_threshold": THRESHOLD,
        "proposal_count": len(rows),
        "reviewed_score_reproduction_count": len(reviewed_rows),
        "proposal_tier_counts": dict(counts),
        "group_count": len(groups),
        "group_priority_counts": dict(group_counts),
        "proposals": rows,
        "review_groups": groups,
        "limitations": [
            "All raw proposals remain in the output; cluttered means source review priority, not no throw.",
            "A clear source-pixel cue cannot verify complete track identity, physical delivery, release or settle.",
            "The 33 reviewed proposals are selected development evidence, not exhaustive independent event truth.",
            "No full-match precision, recall, F1, complete board or simulation-ready state is inferred.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "proposals": len(rows),
                "groups": len(groups),
                "tiers": dict(counts),
                "group_priorities": dict(group_counts),
            }
        )
    )


if __name__ == "__main__":
    main()
