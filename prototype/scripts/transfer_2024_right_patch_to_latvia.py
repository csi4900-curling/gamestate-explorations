"""Compare a non-Latvia-trained patch model on fixed Latvia source reviews."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cap_patch_verifier import score_candidates
from stone_patch_detector import load_model

BASE = ROOT / "validation/throw-event-benchmark"
LAT = BASE / "canada-latvia-2024"
VIDEO = LAT / "source-360p.mp4"
PRIOR = LAT / "full-right-reviewed-frozen-sideview-patch-transfer-development.json"
TRAINING = BASE / "right-sideview-source-diverse-development-v1/training-results.json"
SELECTION = TRAINING.parent / "selection.json"
MODEL = TRAINING.parent / "model.npz"
SCANS = {
    "one_second_greedy": LAT / "full-right-area-first-transfer.json",
    "two_second_greedy": LAT / "full-right-area-gap2-development.json",
    "two_second_global": LAT / "full-right-global-area-development.json",
    "two_second_global_later": LAT / "full-right-global-multi-episode-development.json",
}
OUT = TRAINING.parent / "latvia-fixed-source-review-transfer.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Latvia transfer already exists")
    prior = json.loads(PRIOR.read_text())
    training = json.loads(TRAINING.read_text())
    selection = json.loads(SELECTION.read_text())
    model = load_model(MODEL)
    video_hash = digest(VIDEO)
    if (
        prior["source_video_sha256"] != video_hash
        or training["selection_sha256"] != digest(SELECTION)
        or training["model_sha256"] != digest(MODEL)
        or any(
            s["video_sha256"] == video_hash or "latvia" in s["video"] for s in selection["sources"]
        )
    ):
        raise ValueError("Training or Latvia source lineage differs")
    proposal_rows = {}
    raw_tracks = {}
    for name, path in SCANS.items():
        scan = json.loads(path.read_text())
        if scan["source_sha256"] != video_hash:
            raise ValueError("Latvia scan source differs")
        entries = (
            scan["later_review_proposals"]
            if name.endswith("_later")
            else scan["directional_review_proposals"]
        )
        for row in entries:
            pid = f"{name}:{row['raw_track_id']}:{row.get('episode_index_within_raw_track', 1)}"
            proposal_rows[pid] = row
        if "raw_tracks" in scan:
            raw_tracks[name] = {r["track_id"]: r for r in scan["raw_tracks"]}
    raw_tracks["two_second_global_later"] = raw_tracks["two_second_global"]
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not capture.isOpened() or fps <= 0:
        raise ValueError("Latvia video unreadable")
    rows = []
    try:
        for reference in prior["rows"]:
            pid = reference["proposal_id"]
            variant, track, _ = pid.split(":")
            proposal = proposal_rows[pid]
            points = proposal["observed_prefix_points"]
            if len(points) < 3:
                points = raw_tracks[variant][track]["points"]
            by_time = {point["time_s"]: point for point in points}
            samples = []
            for old in reference["sample_scores"]:
                time = old["time_s"]
                if time not in by_time:
                    raise ValueError(f"Prior Latvia sample absent: {pid}")
                capture.set(cv2.CAP_PROP_POS_FRAMES, round(time * fps))
                ok, frame = capture.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise ValueError(f"Cannot decode Latvia {pid}")
                scored = score_candidates(frame, [{"bbox": by_time[time]["bbox"]}], model)[0]
                samples.append(
                    {
                        "time_s": time,
                        "patch_score": round(scored["patch_score"], 6),
                        "patch_accepted": scored["patch_accepted"],
                    }
                )
            rows.append(
                {
                    "proposal_id": pid,
                    "source_pixel_class": reference["source_pixel_class"],
                    "old_model_any_positive": reference["any_positive_patch"],
                    "new_model_any_positive": any(s["patch_accepted"] for s in samples),
                    "old_model_positive_sample_count": reference["positive_sample_count"],
                    "new_model_positive_sample_count": sum(s["patch_accepted"] for s in samples),
                    "new_model_samples": samples,
                    "physical_throw_verified": False,
                }
            )
    finally:
        capture.release()
    if len(rows) != prior["reviewed_proposal_count"]:
        raise ValueError("Latvia reviewed set changed")
    counts = Counter((r["source_pixel_class"], r["new_model_any_positive"]) for r in rows)
    result = {
        "status": "development_non_latvia_fit_on_selected_latvia_source_pixels_not_event_truth",
        "source_video_sha256": video_hash,
        "input_sha256": {
            "prior_latvia_score": digest(PRIOR),
            "training_selection": digest(SELECTION),
            "training_result": digest(TRAINING),
            "new_model": digest(MODEL),
            **{name: digest(path) for name, path in SCANS.items()},
        },
        "feature_code_sha256": digest(ROOT / "prototype/stone_patch_detector.py"),
        "scorer_code_sha256": digest(ROOT / "prototype/cap_patch_verifier.py"),
        "runner_sha256": digest(Path(__file__)),
        "model_threshold": float(model["threshold"]),
        "reviewed_proposal_count": len(rows),
        "new_model_counts_by_source_pixel_class": {
            cls: {"positive": counts[cls, True], "negative": counts[cls, False]}
            for cls in sorted({r["source_pixel_class"] for r in rows})
        },
        "rows": rows,
        "limitations": [
            "Latvia examples did not enter fitting, but these labels and prior-model failures were inspected before the new model was specified; this is not a blind holdout.",
            "The 53 selected proposal prefixes are correlated same-agent source-pixel reviews, not independent physical throw labels.",
            "A positive stone-like patch can depict handled or displaced stone; a negative cannot prove no delivery.",
            "This does not measure whole-video event recall, precision, F1 or simulation readiness.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps({"paths": len(rows), "counts": result["new_model_counts_by_source_pixel_class"]})
    )


if __name__ == "__main__":
    main()
