"""Score saved right-camera track patches for corridor two-view proposals."""

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


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def selected_points(points):
    if not points:
        return []
    return [points[i] for i in sorted({0, len(points) // 2, len(points) - 1})]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "right-tail", "corroboration", "model", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    tail = json.loads(args.right_tail.read_text())
    corroboration = json.loads(args.corroboration.read_text())
    source_hash = digest(args.video)
    if source_hash != tail["source_sha256"] or source_hash != corroboration[
            "source_sha256"]:
        raise ValueError("Source hash mismatch")
    selected_ids = {m["right_proposal_id"] for row in corroboration["rows"]
                    for m in row["matching_right_proposals"]}
    by_raw_id = {r["raw_track_id"]: r
                 for r in tail["directional_review_proposals"]}
    if (len(by_raw_id) != len(tail["directional_review_proposals"]) or
            any(rid.count(":") != 1 or rid.split(":")[1] not in by_raw_id
                for rid in selected_ids)):
        raise ValueError("Right track IDs differ")
    model = load_model(args.model)
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Cannot open source video")
    rows = []
    try:
        for proposal_id in sorted(selected_ids):
            proposal = by_raw_id[proposal_id.split(":")[1]]
            samples = []
            for point in selected_points(proposal["observed_prefix_points"]):
                t = point["time_s"] - tail["source_time_offset_s"]
                cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (360, 640):
                    samples.append({"source_time_s": point["time_s"],
                                    "status": "decode_failed", "patch_score": None,
                                    "patch_accepted": None})
                    continue
                scored = score_candidates(frame, [{"bbox": point["bbox"]}], model)[0]
                samples.append({"source_time_s": point["time_s"],
                                "status": "scored",
                                "patch_score": round(scored["patch_score"], 5),
                                "patch_accepted": scored["patch_accepted"]})
            accepted = sum(sample["patch_accepted"] is True for sample in samples)
            scored_count = sum(sample["status"] == "scored" for sample in samples)
            rows.append({"right_proposal_id": proposal_id,
                         "colour_claim": proposal["colour_claim"],
                         "direction": proposal["direction"],
                         "sample_count": len(samples),
                         "scored_count": scored_count,
                         "positive_patch_count": accepted,
                         "samples": samples})
    finally:
        cap.release()
    output = {
        "status": "prediction_only_postreview_patch_diagnostic_not_event_truth",
        "source_sha256": source_hash,
        "input_sha256": {"right_tail": digest(args.right_tail),
                         "corroboration": digest(args.corroboration),
                         "model": digest(args.model)},
        "feature_code_sha256": digest(ROOT / "prototype/stone_patch_detector.py"),
        "scorer_code_sha256": digest(ROOT / "prototype/cap_patch_verifier.py"),
        "runner_sha256": digest(Path(__file__)),
        "sample_rule": "first/middle/last observed prefix point; original track bbox; frozen model",
        "model_threshold": float(model["threshold"]),
        "rows": rows,
        "limitations": [
            "Track boxes themselves may be people or equipment, and patch scores do not verify physical identity.",
            "Selected corridor recordings and track inventories were exposed during development.",
            "Three sampled frames cannot establish complete track appearance or throw-event truth.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"right_tracks": len(rows),
                      "positive_in_any_sample": sum(r["positive_patch_count"] > 0
                                                    for r in rows)}))


if __name__ == "__main__":
    main()
