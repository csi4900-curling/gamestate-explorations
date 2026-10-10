"""Score ice-coloured context around reviewed right motion paths."""

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

NONICE_REVIEW_THRESHOLD = 0.44


def digest(path):
    value = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def selected(proposals, review, kind, recording, proposal_hash):
    if kind == "bidirectional":
        source = next((row for row in review["sources"] if row["recording"] == recording), None)
        if source is None or source["probe_sha256"] != proposal_hash:
            raise ValueError("Bidirectional review does not match probe")
        labels = {
            row["raw_track_id"]: row["source_prefix_class"]
            for row in review["rows"]
            if row["recording"] == recording
        }
        all_rows = {row["raw_track_id"]: row for row in proposals["directional_review_proposals"]}
        if len(labels) != sum(row["recording"] == recording for row in review["rows"]):
            raise ValueError("Duplicate reviewed bidirectional path")
        if not set(labels) <= set(all_rows):
            raise ValueError("Reviewed path missing from probe")
        return [(all_rows[track_id], source_class) for track_id, source_class in labels.items()]
    if kind == "entry":
        if review["variant_sha256"] != proposal_hash:
            raise ValueError("Entry source review does not match variant")
        labels = {row["raw_track_id"]: row["sampled_prefix_class"] for row in review["review"]}
        all_rows = {row["raw_track_id"]: row for row in proposals["entry_review_proposals"]}
        if len(labels) != len(review["review"]) or set(labels) != set(all_rows):
            raise ValueError("Entry review must cover every distinct variant path")
        return [(all_rows[track_id], source_class) for track_id, source_class in labels.items()]
    raise ValueError(f"Unknown proposal kind: {kind}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "proposals", "review", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--kind", choices=("bidirectional", "entry"), required=True)
    parser.add_argument("--recording", required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    proposals = json.loads(args.proposals.read_text())
    review = json.loads(args.review.read_text())
    source_hash = digest(args.video)
    if source_hash != proposals["source_sha256"]:
        parser.error("Video and proposal sources differ")
    if args.kind == "entry" and source_hash != review["source_sha256"]:
        parser.error("Video and entry-review sources differ")
    if args.kind == "bidirectional":
        source = next(row for row in review["sources"] if row["recording"] == args.recording)
        if source_hash != source["source_sha256"]:
            parser.error("Video and bidirectional-review sources differ")
    paths = selected(proposals, review, args.kind, args.recording, digest(args.proposals))
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for proposal, source_class in paths:
            points = proposal["observed_prefix_points"]
            event_time = (
                proposal["passage"]["time_s"]
                if args.kind == "bidirectional"
                else proposal["entry_crossing"]["time_s"]
            )
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
                    "raw_track_id": proposal["raw_track_id"],
                    "source_prefix_class": source_class,
                    "sample_times_s": [point["time_s"] for point in chosen],
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
        "status": "development_ice_context_review_score_not_accepted_event_filter",
        "source_sha256": source_hash,
        "recording": args.recording,
        "proposal_kind": args.kind,
        "proposals_sha256": digest(args.proposals),
        "source_review_sha256": digest(args.review),
        "feature_code_sha256": digest(ROOT / "prototype/right_track_ice_context.py"),
        "runner_sha256": digest(Path(__file__)),
        "outer_half_size_px": [28, 40],
        "excluded_inner_half_extent_px": 12,
        "ice_hsv_rule": {"saturation_less_than": 90, "value_greater_than": 150},
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
            "The threshold was chosen after measuring the selected Italy/Estonia/China development paths.",
            "Source classes are same-agent short-prefix reviews, not independent physical-throw labels.",
            "Painted rings, players close to a stone, camera cuts and wheelchair objects can change local ice fraction.",
            "A review tier cannot reject physical throws without independent recall validation.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"rows": len(rows), "counts": result["counts_by_source_class_and_tier"]}))


if __name__ == "__main__":
    main()
