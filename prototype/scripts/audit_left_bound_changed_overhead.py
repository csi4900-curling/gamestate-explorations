"""Measure overhead darkness on all newly unique paired-bound path patches."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from audit_path_overhead_darkness import overhead_dark_fraction  # noqa: E402


def digest(path):
    value = sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    batch = json.loads(args.batch.read_text())
    if digest(args.video) != batch["video_sha256"]:
        parser.error("Video differs from batch")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    output_rows = []
    try:
        for candidate_id in batch["changed_selection_ids"]:
            path = args.batch.parent / f"{candidate_id.lower()}-extended-patch.json"
            result = json.loads(path.read_text())
            paired = args.batch.parent / f"{candidate_id.lower()}-paired.json"
            if (result["candidate_id"] != candidate_id or
                    result["probe_sha256"] != digest(paired) or
                    result["video_sha256"] != batch["video_sha256"] or
                    not result["decision"]["accepted"]):
                raise ValueError(f"Invalid patch result: {path}")
            observations = []
            for sample in result["samples"]:
                if not sample.get("patch_accepted"):
                    continue
                time_s = sample["source_time_s"]
                cap.set(cv2.CAP_PROP_POS_FRAMES,
                        round((time_s - batch["source_offset_s"]) * fps))
                ok, frame = cap.read()
                fraction = (overhead_dark_fraction(frame, sample["cap_bbox_1080p"])
                            if ok else None)
                observations.append({"source_time_s": time_s,
                                     "dark_fraction": fraction,
                                     "decoded_frame_index":
                                     int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1 if ok else None})
            complete = bool(observations) and all(
                x["dark_fraction"] is not None for x in observations)
            minimum = min(x["dark_fraction"] for x in observations) if complete else None
            output_rows.append({"candidate_id": candidate_id,
                                "patch_sha256": digest(path),
                                "frozen_model_sha256": result["model_sha256"],
                                "positive_patch_count": len(observations),
                                "complete": complete,
                                "minimum_overhead_dark_fraction": minimum,
                                "would_abstain_at_0_75": complete and minimum >= 0.75,
                                "samples": observations})
    finally:
        cap.release()
    if len(output_rows) != len(batch["changed_selection_ids"]):
        raise ValueError("Changed candidate coverage differs")
    output = {
        "status": "postscore_development_changed_path_overhead_audit_not_validation",
        "source_sha256": batch["video_sha256"],
        "batch_sha256": digest(args.batch),
        "feature_code_sha256": digest(ROOT / "prototype/scripts/audit_path_overhead_darkness.py"),
        "runner_sha256": digest(Path(__file__)),
        "threshold": 0.75,
        "changed_candidate_count": len(output_rows),
        "all_complete": all(r["complete"] for r in output_rows),
        "would_abstain_candidate_ids": [r["candidate_id"] for r in output_rows
                                        if r["would_abstain_at_0_75"]],
        "rows": output_rows,
        "limitations": [
            "The feature and threshold were chosen after exposed false-path review.",
            "These source-visible paths are not independently labelled full throw events.",
            "Darkness at three sampled locations does not verify identity along the whole path.",
        ],
    }
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(len(output_rows), "changed paths; would abstain",
          output["would_abstain_candidate_ids"])


if __name__ == "__main__":
    main()
