"""Score all area-aware right proposals with the frozen 2024 context pair."""

import argparse
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


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "video", "probe", "episodes", "source-review", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    plan, probe, episodes, review = (
        json.loads(path.read_text())
        for path in (args.plan, args.probe, args.episodes, args.source_review)
    )
    expected = {
        "source_sha256": digest(args.video),
        "probe_sha256": digest(args.probe),
        "episodes_sha256": digest(args.episodes),
        "source_review_sha256": digest(args.source_review),
        "ring_feature_code_sha256": digest(ROOT / "prototype/right_track_ice_context.py"),
        "underpoint_feature_code_sha256": digest(
            ROOT / "prototype/right_track_underpoint_context.py"
        ),
    }
    if any(plan[key] != value for key, value in expected.items()):
        raise ValueError("Frozen source, inputs or feature code changed")
    if (
        probe["source_sha256"] != expected["source_sha256"]
        or episodes["source_sha256"] != expected["source_sha256"]
        or review["source_sha256"] != expected["source_sha256"]
        or episodes["input_sha256"]["right"] != expected["probe_sha256"]
    ):
        raise ValueError("Source lineage differs")
    label_by_id = {row["right_proposal_id"]: row["sampled_prefix_class"] for row in review["rows"]}
    if len(label_by_id) != len(review["rows"]):
        raise ValueError("Duplicate source-review ID")
    episode_by_right = {}
    for episode in episodes["episodes"]:
        for rid in episode["right_proposal_ids"]:
            if rid in episode_by_right:
                raise ValueError("Right proposal appears in multiple episodes")
            episode_by_right[rid] = episode
    tracks = {"R01:" + row["raw_track_id"]: row for row in probe["directional_review_proposals"]}
    if (
        len(tracks) != len(probe["directional_review_proposals"])
        or set(episode_by_right) != set(tracks)
        or not set(label_by_id) <= set(tracks)
        or any(
            episode_by_right[rid]["episode_kind"] != "right_only_candidate" for rid in label_by_id
        )
    ):
        raise ValueError("Review or episode inventory differs")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for rid, track in sorted(tracks.items()):
            points = track["observed_prefix_points"]
            t = track["passage"]["time_s"]
            chosen = [points[0], min(points, key=lambda p: abs(p["time_s"] - t)), points[-1]]
            episode = episode_by_right[rid]
            row = {
                "right_proposal_id": rid,
                "episode_id": episode["episode_id"],
                "episode_kind": episode["episode_kind"],
                "source_prefix_class": label_by_id.get(rid),
                "sample_source_times_s": [p["time_s"] for p in chosen],
                "distinct_sample_count": len({p["time_s"] for p in chosen}),
                "physical_stone_identity_verified": False,
            }
            if row["distinct_sample_count"] < 3:
                row["review_tier"] = "insufficient_distinct_samples"
                rows.append(row)
                continue
            frames = []
            for point in chosen:
                frame_index = round((point["time_s"] - probe["source_time_offset_s"]) * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise RuntimeError(f"Cannot decode frame {frame_index}")
                frames.append(frame)
            ring = three_sample_context(frames, chosen)
            under = three_sample_underpoint(frames, chosen)
            ring_fraction = ring["median_nonice_ring_fraction"]
            under_fraction = under["median_underpoint_nonice_fraction"]
            row.update(
                {
                    "sample_nonice_ring_fractions": ring["sample_nonice_ring_fractions"],
                    "median_nonice_ring_fraction": ring_fraction,
                    "sample_underpoint_nonice_fractions": under[
                        "sample_underpoint_nonice_fractions"
                    ],
                    "median_underpoint_nonice_fraction": under_fraction,
                    "underpoint_available_sample_count": under["available_sample_count"],
                    "review_tier": (
                        "underpoint_unavailable"
                        if under_fraction is None
                        else "cluttered_context_review"
                        if max(ring_fraction, under_fraction) > 0.25
                        else "clear_context_review"
                    ),
                }
            )
            rows.append(row)
    finally:
        cap.release()
    by_kind = Counter((r["episode_kind"], r["review_tier"]) for r in rows)
    by_class = Counter(
        (r["source_prefix_class"], r["review_tier"])
        for r in rows
        if r["source_prefix_class"] is not None
    )
    output = {
        "status": "frozen_feature_area_right_transfer_review_score_not_event_decision",
        "source_sha256": expected["source_sha256"],
        "input_sha256": {
            "plan": digest(args.plan),
            "probe": digest(args.probe),
            "episodes": digest(args.episodes),
            "source_review": digest(args.source_review),
        },
        "ring_feature_code_sha256": expected["ring_feature_code_sha256"],
        "underpoint_feature_code_sha256": expected["underpoint_feature_code_sha256"],
        "runner_sha256": digest(Path(__file__)),
        "review_threshold": 0.25,
        "proposal_count": len(rows),
        "reviewed_right_only_count": len(label_by_id),
        "counts_by_episode_kind_and_tier": {
            kind: {tier: count for (k, tier), count in sorted(by_kind.items()) if k == kind}
            for kind in sorted({r["episode_kind"] for r in rows})
        },
        "counts_by_source_prefix_class_and_tier": {
            source_class: {
                tier: count for (k, tier), count in sorted(by_class.items()) if k == source_class
            }
            for source_class in sorted(set(label_by_id.values()))
        },
        "rows": rows,
        "limitations": [
            "Source classes are postproposal same-agent three-frame reviews, not independent throw labels.",
            "A clear score does not establish physical stone identity, delivery, or full-video recall.",
            "The 2024 camera family and ice context may differ from other recordings.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {
                "proposals": len(rows),
                "reviewed_classes": output["counts_by_source_prefix_class_and_tier"],
            }
        )
    )


if __name__ == "__main__":
    main()
