"""Transfer existing image-context cues to reviewed Latvia right proposals."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from right_track_ice_context import three_sample_context
from right_track_underpoint_context import three_sample_underpoint
from right_context_tier import context_tier

BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
VIDEO = BASE / "source-360p.mp4"
QUEUE = BASE / "full-right-variant-review-queue-development.json"
SINGLE = BASE / "full-right-variant-singleton-source-audit.json"
DOUBLE = BASE / "full-right-two-variant-source-audit.json"
SCANS = {
    "one_second_greedy": BASE / "full-right-area-first-transfer.json",
    "two_second_greedy": BASE / "full-right-area-gap2-development.json",
    "two_second_global": BASE / "full-right-global-area-development.json",
    "two_second_global_later": BASE / "full-right-global-multi-episode-development.json",
}
OUT = BASE / "full-right-reviewed-context-transfer-development.json"
PRIOR_RING_THRESHOLD = 0.44
FROZEN_PAIRED_THRESHOLD = 0.25


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    queue = json.loads(QUEUE.read_text())
    single = json.loads(SINGLE.read_text())
    double = json.loads(DOUBLE.read_text())
    scans = {name: json.loads(path.read_text()) for name, path in SCANS.items()}
    video_hash = digest(VIDEO)
    if queue["source_video_sha256"] != video_hash or any(
        scan["source_sha256"] != video_hash or queue["input_sha256"][name] != digest(SCANS[name])
        for name, scan in scans.items()
    ):
        raise ValueError("Source/scan lineage mismatch")
    if single["input_sha256"]["queue"] != digest(QUEUE) or double["input_sha256"][
        "queue"
    ] != digest(QUEUE):
        raise ValueError("Review audits do not match queue")
    labels = {row["proposal_id"]: row["source_pixel_class"] for row in single["rows"]}
    for group in double["rows"]:
        for member in group["members"]:
            pid = member["proposal_id"]
            if pid in labels:
                raise ValueError("Duplicate review label")
            labels[pid] = member["source_pixel_class"]
    if len(labels) != 33:
        raise ValueError("Expected 33 reviewed proposal identities")
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
            proposal_rows[pid] = row
        if "raw_tracks" in scan:
            raw_tracks[name] = {r["track_id"]: r for r in scan["raw_tracks"]}
    raw_tracks["two_second_global_later"] = raw_tracks["two_second_global"]
    if not set(labels) <= set(proposal_rows):
        raise ValueError("Reviewed proposal absent from scan")
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not capture.isOpened() or fps <= 0:
        raise ValueError("Source unreadable")
    rows = []
    try:
        for pid in sorted(labels):
            proposal = proposal_rows[pid]
            points = proposal["observed_prefix_points"]
            if len(points) < 3:
                points = raw_tracks[pid.split(":")[0]][proposal["raw_track_id"]]["points"]
                policy = "nearest_three_raw_track_points"
            else:
                policy = "nearest_three_prefix_points"
            passage_time = proposal["passage"]["time_s"]
            chosen = sorted(
                sorted(points, key=lambda p: (abs(p["time_s"] - passage_time), p["time_s"]))[:3],
                key=lambda p: p["time_s"],
            )
            if len(chosen) != 3:
                raise ValueError("Insufficient source samples")
            frames = []
            for point in chosen:
                capture.set(cv2.CAP_PROP_POS_FRAMES, round(point["time_s"] * fps))
                ok, frame = capture.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise ValueError(f"Unreadable source sample: {pid}")
                frames.append(frame)
            ring = three_sample_context(frames, chosen)
            under = three_sample_underpoint(frames, chosen)
            rows.append(
                {
                    "proposal_id": pid,
                    "source_pixel_class": labels[pid],
                    "passage_time_s": passage_time,
                    "sample_times_s": [point["time_s"] for point in chosen],
                    "sampling_policy": policy,
                    "median_nonice_ring_fraction": ring["median_nonice_ring_fraction"],
                    "sample_nonice_ring_fractions": ring["sample_nonice_ring_fractions"],
                    "median_underpoint_nonice_fraction": under["median_underpoint_nonice_fraction"],
                    "sample_underpoint_nonice_fractions": under[
                        "sample_underpoint_nonice_fractions"
                    ],
                    "prior_isolated_ice_context": ring["median_nonice_ring_fraction"]
                    <= PRIOR_RING_THRESHOLD,
                    "frozen_paired_context_tier": context_tier(
                        ring["median_nonice_ring_fraction"],
                        under["median_underpoint_nonice_fraction"],
                        threshold=FROZEN_PAIRED_THRESHOLD,
                    ),
                    "physical_throw_verified": False,
                }
            )
    finally:
        capture.release()
    counts = Counter((row["source_pixel_class"], row["prior_isolated_ice_context"]) for row in rows)
    classes = sorted({row["source_pixel_class"] for row in rows})
    paired_counts = Counter(
        (row["source_pixel_class"], row["frozen_paired_context_tier"]) for row in rows
    )
    result = {
        "status": "development_transfer_of_existing_context_cues_not_event_filter",
        "source_video_sha256": video_hash,
        "input_sha256": {
            "queue": digest(QUEUE),
            "singleton_audit": digest(SINGLE),
            "two_variant_audit": digest(DOUBLE),
            **{name: digest(path) for name, path in SCANS.items()},
        },
        "feature_code_sha256": {
            "ring": digest(ROOT / "prototype/right_track_ice_context.py"),
            "underpoint": digest(ROOT / "prototype/right_track_underpoint_context.py"),
            "paired_tier": digest(ROOT / "prototype/right_context_tier.py"),
        },
        "runner_sha256": digest(Path(__file__)),
        "prior_ring_threshold": PRIOR_RING_THRESHOLD,
        "frozen_paired_threshold": FROZEN_PAIRED_THRESHOLD,
        "reviewed_proposal_count": len(rows),
        "counts_by_class_and_prior_ring_tier": {
            cls: {"isolated": counts[cls, True], "cluttered": counts[cls, False]} for cls in classes
        },
        "counts_by_class_and_frozen_paired_tier": {
            cls: {
                "clear": paired_counts[cls, "clear_context_review"],
                "cluttered": paired_counts[cls, "context_cluttered_review"],
                "unavailable": paired_counts[cls, "context_unavailable_review"],
            }
            for cls in classes
        },
        "rows": rows,
        "limitations": [
            "These 33 selected proposal prefixes are not an independent or exhaustive physical-throw test set.",
            "A source-visible stone can have a cluttered context near players or painted rings.",
            "The prior 0.44 ring and 0.25 paired thresholds were chosen on other development recordings, not calibrated here.",
            "No cue here decides a complete same-stone track, throw identity or game state.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "proposals": len(rows),
                "paired_counts": result["counts_by_class_and_frozen_paired_tier"],
            }
        )
    )


if __name__ == "__main__":
    main()
