"""Apply the fixed non-ice review cue to every right proposal in an offset clip."""

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
    result = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "probe", "source_review", "output"):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    probe = json.loads(args.probe.read_text())
    review = json.loads(args.source_review.read_text())
    source_hash = digest(args.video)
    if (
        probe["source_sha256"] != source_hash
        or review["source_sha256"] != source_hash
        or review["probe_sha256"] != digest(args.probe)
    ):
        parser.error("Probe, review and video provenance differs")
    labels = {row["raw_track_id"]: row["source_prefix_class"] for row in review["rows"]}
    proposals = probe["directional_review_proposals"]
    if len(labels) != len(review["rows"]) or set(labels) != {
        row["raw_track_id"] for row in proposals
    }:
        parser.error("Source review must cover every distinct proposal")
    offset = probe["source_time_offset_s"]
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open source clip")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for proposal in proposals:
            points = proposal["observed_prefix_points"]
            event_t = proposal["passage"]["time_s"]
            chosen = [
                points[0],
                min(points, key=lambda point: abs(point["time_s"] - event_t)),
                points[-1],
            ]
            frames = []
            for point in chosen:
                local_t = point["time_s"] - offset
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(local_t * fps))
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f"Could not decode clip time {local_t}")
                frames.append(cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA))
            score = three_sample_context(frames, chosen)
            rows.append(
                {
                    "raw_track_id": proposal["raw_track_id"],
                    "source_prefix_class": labels[proposal["raw_track_id"]],
                    "sample_source_times_s": [point["time_s"] for point in chosen],
                    **score,
                    "review_tier": (
                        "isolated_ice_context"
                        if score["median_nonice_ring_fraction"] <= NONICE_REVIEW_THRESHOLD
                        else "context_cluttered_review"
                    ),
                }
            )
    finally:
        cap.release()
    counts = Counter((row["source_prefix_class"], row["review_tier"]) for row in rows)
    result = {
        "status": "fixed_ice_context_clip_transfer_not_physical_throw_classifier",
        "source_sha256": source_hash,
        "probe_sha256": digest(args.probe),
        "source_review_sha256": digest(args.source_review),
        "feature_code_sha256": digest(ROOT / "prototype/right_track_ice_context.py"),
        "runner_sha256": digest(Path(__file__)),
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
            "The source classes are same-agent short-prefix reviews, not physical-delivery truth.",
            "The 0.25 threshold came from exposed 2024 recordings before this clip was scored, but this is not an independent end evaluation.",
            "A low non-ice score may still belong to clothing or equipment over the rink.",
            "No event is accepted or rejected by this review cue.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"rows": len(rows), "counts": result["counts_by_source_class_and_tier"]}))


if __name__ == "__main__":
    main()
