"""Transfer the fixed expanded right-camera backtracking probe to a match."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from expanded_right_colour import expanded_right_colour_proposals
from right_backward_seam import backward_extension


def digest(path):
    result = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--right-proposals", type=Path, required=True)
    parser.add_argument("--source-review", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    proposals = json.loads(args.right_proposals.read_text())
    source_hash = digest(args.video)
    if source_hash != proposals["source_sha256"]:
        parser.error("Video and proposal source hashes disagree")
    review = None
    classes = {}
    if args.source_review:
        review = json.loads(args.source_review.read_text())
        if review["source_sha256"] != source_hash or review["variant_sha256"] != digest(
            args.right_proposals
        ):
            parser.error("Source review and proposal hashes disagree")
        classes = {row["raw_track_id"]: row["sampled_prefix_class"] for row in review["review"]}
        if len(classes) != len(review["review"]):
            parser.error("Duplicate reviewed prefix")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    cache = {}

    def source_proposals(time_s, colour):
        if time_s not in cache:
            cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Cannot decode {time_s} s")
            cache[time_s] = expanded_right_colour_proposals(frame)
        return cache[time_s][colour]

    rows = []
    try:
        for proposal in proposals["entry_review_proposals"]:
            first = proposal["observed_prefix_points"][0]
            extension = backward_extension(
                first, first["time_s"] - 8, proposal["colour_claim"], source_proposals
            )
            rows.append(
                {
                    "right_raw_track_id": proposal["raw_track_id"],
                    "colour_claim": proposal["colour_claim"],
                    "original_first_observed_s": first["time_s"],
                    "conditional_first_observed_s": extension["new_first_observed_s"],
                    "added_duration_s": round(
                        first["time_s"] - extension["new_first_observed_s"], 3
                    ),
                    "development_source_prefix_class": classes.get(proposal["raw_track_id"]),
                    **extension,
                }
            )
    finally:
        cap.release()
    by_class = defaultdict(lambda: {"prefixes": 0, "extended": 0})
    for row in rows:
        label = row["development_source_prefix_class"] or "unreviewed"
        by_class[label]["prefixes"] += 1
        by_class[label]["extended"] += bool(row["added_observations"])
    output = {
        "status": "right_prefix_backward_transfer_diagnostic_not_throw_score",
        "source_sha256": source_hash,
        "input_sha256": {
            "right_proposals": digest(args.right_proposals),
            "source_review": digest(args.source_review) if args.source_review else None,
        },
        "expanded_detector_code_sha256": digest(ROOT / "prototype/expanded_right_colour.py"),
        "extension_code_sha256": digest(ROOT / "prototype/right_backward_seam.py"),
        "runner_sha256": digest(Path(__file__)),
        "prefix_count": len(rows),
        "extended_prefix_count": sum(bool(row["added_observations"]) for row in rows),
        "development_class_counts": dict(by_class),
        "stop_reason_counts": dict(Counter(row["stop_reason"] for row in rows)),
        "rows": rows,
        "limitations": [
            "Expansion thresholds were selected after inspecting Scotland and are fixed for this transfer.",
            "Source classes are same-agent three-frame development reviews, not independent throw labels.",
            "Earlier coloured pixels can belong to another object; backtracking is not a physical identity test.",
            "This positive-selected probe cannot measure full-match throw recall, precision or F1.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "prefixes": len(rows),
                "extended": output["extended_prefix_count"],
                "development_classes": output["development_class_counts"],
            }
        )
    )


if __name__ == "__main__":
    main()
