"""Diagnostic frozen patch scores at exact 2024 passage locations."""

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
from throw_detection import PassageConfig, stone_candidates


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--timeline", required=True, type=Path)
    parser.add_argument("--baseline-timeline", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve prior diagnostic")
    timeline = json.loads(args.timeline.read_text())
    baseline = json.loads(args.baseline_timeline.read_text())
    if digest(args.video) != timeline["source_sha256"]:
        parser.error("Source fingerprint differs")
    if timeline["source_sha256"] != baseline["source_sha256"]:
        parser.error("Timeline source fingerprints differ")
    model = load_model(args.model)
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened() or fps <= 0:
        parser.error("Unreadable video")
    config = PassageConfig()
    rows = []
    for event in timeline["observed_events"]:
        t = event["crossing_time_s"]
        original = any(prior["colour"] == event["colour"] and
                       abs(prior["crossing_time_s"] - t) <= 0.25
                       for prior in baseline["observed_events"])
        samples = []
        for offset in (-0.2, 0.0, 0.2):
            seconds = t + offset
            cap.set(cv2.CAP_PROP_POS_FRAMES, round(seconds * fps))
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Cannot decode {seconds:.3f}")
            coloured = [row for row in stone_candidates(frame, config)
                        if row["colour"] == event["colour"]]
            scored = score_candidates(frame, coloured, model)
            ranked = sorted(scored, key=lambda row: (
                (row["pixel"][0] - event["crossing_x_px"]) ** 2 +
                (row["pixel"][1] - event["passage_y_px"]) ** 2))
            closest = ranked[0] if ranked else None
            distance = (((closest["pixel"][0] - event["crossing_x_px"]) ** 2 +
                         (closest["pixel"][1] - event["passage_y_px"]) ** 2) ** 0.5
                        if closest else None)
            matched = closest if distance is not None and distance <= 12 else None
            samples.append({
                "time_s": round(seconds, 3),
                "same_colour_candidate_count": len(scored),
                "nearest_distance_px": round(distance, 3) if distance is not None else None,
                "matched_within_12px": matched is not None,
                "matched_bbox": matched["bbox"] if matched else None,
                "matched_patch_score": matched["patch_score"] if matched else None,
                "matched_patch_accepted": matched["patch_accepted"] if matched else None,
            })
        rows.append({
            "event_id": event["id"],
            "candidate_time_s": t,
            "colour_claim": event["colour"],
            "group": "baseline_candidate" if original else "bridged_review_candidate",
            "matched_samples": sum(row["matched_within_12px"] for row in samples),
            "accepted_patch_samples": sum(row["matched_patch_accepted"] is True
                                          for row in samples),
            "max_matched_patch_score": max(
                (row["matched_patch_score"] for row in samples
                 if row["matched_patch_score"] is not None), default=None),
            "samples": samples,
        })
    cap.release()
    result = {
        "status": "postscore_crossing_patch_diagnostic_not_stone_identity_validation",
        "source_sha256": timeline["source_sha256"],
        "timeline_sha256": digest(args.timeline),
        "baseline_timeline_sha256": digest(args.baseline_timeline),
        "model_sha256": digest(args.model),
        "runner_sha256": digest(Path(__file__)),
        "match_radius_px": 12,
        "offsets_s": [-0.2, 0, 0.2],
        "events": rows,
        "limitations": [
            "Nearest same-colour pixels may belong to a player, broom, or another stone.",
            "The frozen patch model was trained on selected 2022 crops, not this source.",
            "Three local samples and an appearance score cannot verify physical delivery identity.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"events": len(rows), "bridged": sum(
        row["group"] == "bridged_review_candidate" for row in rows)}))


if __name__ == "__main__":
    main()
