"""Transfer the 2024 right-track ice-context cue to Scotland source reviews."""

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

NONICE_REVIEW_THRESHOLD = 0.25


def digest(path):
    value = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "variant", "fusion", "source_review", "output"):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    variant = json.loads(args.variant.read_text())
    fusion = json.loads(args.fusion.read_text())
    review = json.loads(args.source_review.read_text())
    source_hash = digest(args.video)
    if any(item["source_sha256"] != source_hash for item in (variant, fusion, review)):
        parser.error("Source fingerprints differ")
    if fusion["right_sha256"] != digest(args.variant) or review["fusion_v2_sha256"] != digest(
        args.fusion
    ):
        parser.error("Variant, fusion and source review lineage differs")
    proposals = {row["raw_track_id"]: row for row in variant["entry_review_proposals"]}
    reviewed = {row["right_raw_track_id"]: row for row in review["review"]}
    if (
        len(proposals) != len(variant["entry_review_proposals"])
        or len(reviewed) != len(review["review"])
        or not set(reviewed) <= set(proposals)
    ):
        parser.error("Invalid or duplicate reviewed right prefix")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for raw_id, source_review in reviewed.items():
            proposal = proposals[raw_id]
            points = proposal["observed_prefix_points"]
            event_time = proposal["entry_crossing"]["time_s"]
            chosen = [
                points[0],
                min(points, key=lambda p: abs(p["time_s"] - event_time)),
                points[-1],
            ]
            frames = []
            for point in chosen:
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(point["time_s"] * fps))
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise RuntimeError(f"Could not decode source time {point['time_s']}")
                frames.append(frame)
            score = three_sample_context(frames, chosen)
            rows.append(
                {
                    "right_raw_track_id": raw_id,
                    "source_prefix_class": source_review["sampled_prefix_class"],
                    "sample_times_s": [point["time_s"] for point in chosen],
                    **score,
                    "review_tier_at_0_25": (
                        "isolated_ice_context"
                        if score["median_nonice_ring_fraction"] <= NONICE_REVIEW_THRESHOLD
                        else "context_cluttered_review"
                    ),
                }
            )
    finally:
        cap.release()
    counts = Counter((row["source_prefix_class"], row["review_tier_at_0_25"]) for row in rows)
    result = {
        "status": "scotland_selected_right_ice_context_transfer_not_event_classifier",
        "source_sha256": source_hash,
        "variant_sha256": digest(args.variant),
        "fusion_sha256": digest(args.fusion),
        "source_review_sha256": digest(args.source_review),
        "feature_code_sha256": digest(ROOT / "prototype/right_track_ice_context.py"),
        "runner_sha256": digest(Path(__file__)),
        "reviewed_prefix_count": len(rows),
        "nonice_review_threshold": NONICE_REVIEW_THRESHOLD,
        "counts_by_source_class_and_tier": {
            source_class: {
                tier: counts[source_class, tier]
                for tier in ("isolated_ice_context", "context_cluttered_review")
            }
            for source_class in sorted({row["source_prefix_class"] for row in rows})
        },
        "rows": rows,
        "limitations": [
            "Only the 11 prefixes without original-route corroboration had source-reviewed classes.",
            "The 0.25 threshold was selected after inspecting other exposed 2024 paths; Scotland is development transfer, not independent validation.",
            "Ice context can be confounded by players, rings, occlusion, and camera cuts.",
            "This remains a review tier and does not accept or reject physical throws.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"rows": len(rows), "counts": result["counts_by_source_class_and_tier"]}))


if __name__ == "__main__":
    main()
