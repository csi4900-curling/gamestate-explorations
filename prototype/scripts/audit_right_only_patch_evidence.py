"""Score right-only episode tracks with the existing frozen patch model."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cap_patch_verifier import score_candidates
from stone_patch_detector import load_model
from scripts.audit_corridor_right_patch_evidence import selected_points


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "right-tail", "episodes", "model", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    tail = json.loads(args.right_tail.read_text())
    episodes = json.loads(args.episodes.read_text())
    if (digest(args.video) != tail["source_sha256"] or
            episodes["source_sha256"] != tail["source_sha256"] or
            episodes["right_tail_sha256"] != digest(args.right_tail)):
        raise ValueError("Source or right-tail lineage differs")
    right_only = [row for row in episodes["episodes"]
                  if row["episode_kind"] == "right_only_candidate"]
    by_raw = {row["raw_track_id"]: row
              for row in tail["directional_review_proposals"]}
    if len(by_raw) != len(tail["directional_review_proposals"]):
        raise ValueError("Duplicate raw right track ID")
    model = load_model(args.model)
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Cannot open source video")
    rows = []
    try:
        for episode in right_only:
            rid = episode["right_proposal_ids"][0]
            raw_id = rid.split(":", 1)[1]
            if raw_id not in by_raw:
                raise ValueError("Unknown right-only track")
            track = by_raw[raw_id]
            samples = []
            for point in selected_points(track["observed_prefix_points"]):
                t = point["time_s"] - tail["source_time_offset_s"]
                cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (360, 640):
                    samples.append({"source_time_s": point["time_s"],
                                    "status": "decode_failed", "patch_score": None,
                                    "patch_accepted": None})
                    continue
                score = score_candidates(frame, [{"bbox": point["bbox"]}], model)[0]
                samples.append({"source_time_s": point["time_s"],
                                "status": "scored",
                                "patch_score": round(score["patch_score"], 5),
                                "patch_accepted": score["patch_accepted"]})
            rows.append({"episode_id": episode["episode_id"],
                         "right_proposal_id": rid,
                         "observation_time_s": episode["observation_time_s"],
                         "colour_claim": episode["colour_claim"],
                         "positive_patch_count": sum(
                             item["patch_accepted"] is True for item in samples),
                         "scored_count": sum(item["status"] == "scored"
                                             for item in samples),
                         "samples": samples})
    finally:
        cap.release()
    output = {
        "status": "postscan_right_only_appearance_diagnostic_not_throw_truth",
        "source_id": episodes["source_id"],
        "source_sha256": episodes["source_sha256"],
        "input_sha256": {"right_tail": digest(args.right_tail),
                         "episodes": digest(args.episodes),
                         "model": digest(args.model)},
        "scorer_code_sha256": digest(ROOT / "prototype/cap_patch_verifier.py"),
        "feature_code_sha256": digest(ROOT / "prototype/stone_patch_detector.py"),
        "runner_sha256": digest(Path(__file__)),
        "model_threshold": float(model["threshold"]),
        "right_only_track_count": len(rows),
        "rows": rows,
        "limitations": [
            "The appearance model missed real coarse-window matches on Canada–China; a negative is not a non-throw label.",
            "Positive stone-like patches can depict handled or displaced stones, not a delivery.",
            "Sampling three tracked boxes does not verify physical track identity or complete-video recall.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"right_only_tracks": len(rows),
                      "positive_3_of_3": sum(row["positive_patch_count"] == 3
                                             for row in rows)}))


if __name__ == "__main__":
    main()
