"""Score fixed ice-context cues around stable pre/post right-panel caps."""

import argparse
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


def digest(path):
    value = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "pre", "post", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    pre, post = [json.loads(path.read_text()) for path in (args.pre, args.post)]
    source_hash = digest(args.video)
    if (
        len({source_hash, pre["source_sha256"], post["source_sha256"]}) != 1
        or pre["candidate_sequence_sha256"] != post["candidate_sequence_sha256"]
    ):
        parser.error("Source or candidate sequence fingerprints differ")
    pre_ids = {row["candidate_id"] for row in pre["rows"]}
    post_ids = {row["candidate_id"] for row in post["rows"]}
    if (
        len(pre_ids) != len(pre["rows"])
        or len(post_ids) != len(post["rows"])
        or pre_ids != post_ids
    ):
        parser.error("Pre and post candidate sets differ")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Unreadable source video")
    rows = []
    try:
        for phase, scan in (("pre", pre), ("post", post)):
            for event in scan["rows"]:
                if not event["stable_cap_proposals"]:
                    continue
                frames = []
                for t in event["sample_times_s"]:
                    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
                    ok, frame = cap.read()
                    if not ok or frame.shape[:2] != (360, 640):
                        raise RuntimeError(f"Cannot decode source frame at {t}")
                    frames.append(frame)
                for item in event["stable_cap_proposals"]:
                    points = [{"pixel": item["pixel_center"]}] * 3
                    ring = three_sample_context(frames, points)
                    under = three_sample_underpoint(frames, points)
                    ring_value = ring["median_nonice_ring_fraction"]
                    under_value = under["median_underpoint_nonice_fraction"]
                    rows.append(
                        {
                            "candidate_id": event["candidate_id"],
                            "phase": phase,
                            "local_observation_id": item["local_observation_id"],
                            "colour": item["colour"],
                            "pixel_center": item["pixel_center"],
                            "sample_source_times_s": event["sample_times_s"],
                            "median_nonice_ring_fraction": ring_value,
                            "median_underpoint_nonice_fraction": under_value,
                            "context_tier": context_tier(ring_value, under_value),
                            "physical_stone_identity_verified": False,
                        }
                    )
    finally:
        cap.release()
    counts = Counter(row["context_tier"] for row in rows)
    result = {
        "status": "fixed_context_review_cue_on_partial_board_caps_not_stone_classifier",
        "source_sha256": source_hash,
        "input_sha256": {
            "pre_cap_scan": digest(args.pre),
            "post_cap_scan": digest(args.post),
            "candidate_sequence": pre["candidate_sequence_sha256"],
        },
        "ring_feature_sha256": digest(ROOT / "prototype/right_track_ice_context.py"),
        "underpoint_feature_sha256": digest(ROOT / "prototype/right_track_underpoint_context.py"),
        "tier_code_sha256": digest(ROOT / "prototype/right_context_tier.py"),
        "runner_sha256": digest(Path(__file__)),
        "nonice_threshold": 0.25,
        "cap_count": len(rows),
        "context_tier_counts": dict(counts),
        "rows": rows,
        "limitations": [
            "A clear context may still contain a handled stone, signage or equipment.",
            "A cluttered context may hide a real stone near a player.",
            "The same threshold was transferred from moving right paths, not validated for settled boards.",
            "No cap is promoted to a physical stone, complete board, or game state.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"caps": len(rows), "tiers": dict(counts)}))


if __name__ == "__main__":
    main()
