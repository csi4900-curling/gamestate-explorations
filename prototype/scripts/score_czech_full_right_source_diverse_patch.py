"""Transfer the frozen 2024 right-view patch model to every Czech right proposal."""

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
CZECH = BASE / "canada-czech-2024"
VIDEO = CZECH / "source-360p.mp4"
SCAN = CZECH / "full-corridor-right-tail-first-transfer.json"
MODEL = BASE / "right-sideview-source-diverse-development-v1/model.npz"
TRAINING = MODEL.parent / "training-results.json"
SELECTION = MODEL.parent / "selection.json"
CONTROLS = CZECH / "full-corridor-right-only-top-patch-review/source-review.json"
OUT = CZECH / "full-right-source-diverse-patch-transfer-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def sample_points(proposal):
    points = proposal["observed_prefix_points"]
    if len(points) < 2:
        raise ValueError("Right proposal has too few prefix points")
    indices = sorted({0, (len(points) - 1) // 2, len(points) - 1})
    return [points[index] for index in indices]


def main():
    if OUT.exists():
        raise ValueError("Czech score artifact already exists")
    scan = json.loads(SCAN.read_text())
    training = json.loads(TRAINING.read_text())
    selection = json.loads(SELECTION.read_text())
    controls = json.loads(CONTROLS.read_text())
    source_hash = digest(VIDEO)
    if (
        scan["source_sha256"] != source_hash
        or scan["directional_proposal_count"] != 131
        or len(scan["directional_review_proposals"]) != 131
        or training["model_sha256"] != digest(MODEL)
        or training["selection_sha256"] != digest(SELECTION)
        or controls["source_sha256"] != source_hash
        or any(item["video_sha256"] == source_hash for item in selection["sources"])
    ):
        raise ValueError("Source, proposal, control or model lineage mismatch")
    model = load_model(MODEL)
    if float(model["threshold"]) != 0:
        raise ValueError("Frozen threshold changed")
    requests = []
    for proposal in scan["directional_review_proposals"]:
        pid = "R01:" + proposal["raw_track_id"]
        for point in sample_points(proposal):
            requests.append((point["time_s"], pid, point["bbox"]))
    if len({(time, pid) for time, pid, _ in requests}) != len(requests):
        raise ValueError("Duplicate proposal sample time")
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not capture.isOpened() or fps <= 0:
        raise ValueError("Czech video unreadable")
    by_proposal = {}
    try:
        for time, pid, bbox in sorted(requests):
            capture.set(cv2.CAP_PROP_POS_FRAMES, round(time * fps))
            ok, frame = capture.read()
            if not ok or frame.shape[:2] != (360, 640):
                raise ValueError(f"Czech source decode failed: {pid} {time}")
            score = score_candidates(frame, [{"bbox": bbox}], model)[0]
            by_proposal.setdefault(pid, []).append(
                {
                    "time_s": time,
                    "cap_bbox_px": bbox,
                    "patch_score": round(score["patch_score"], 6),
                    "patch_accepted": score["patch_accepted"],
                }
            )
    finally:
        capture.release()
    rows = []
    for proposal in scan["directional_review_proposals"]:
        pid = "R01:" + proposal["raw_track_id"]
        samples = sorted(by_proposal[pid], key=lambda row: row["time_s"])
        rows.append(
            {
                "right_proposal_id": pid,
                "colour_claim": proposal["colour_claim"],
                "direction": proposal["direction"],
                "passage_time_s": proposal["passage"]["time_s"],
                "any_positive_patch": any(row["patch_accepted"] for row in samples),
                "positive_patch_count": sum(row["patch_accepted"] for row in samples),
                "samples": samples,
                "physical_throw_verified": False,
            }
        )
    control_ids = {row["right_proposal_id"] for row in controls["rows"]}
    if control_ids != {"R01:A035", "R01:A100"}:
        raise ValueError("Source-reviewed controls changed")
    by_id = {row["right_proposal_id"]: row for row in rows}
    counts = Counter(row["positive_patch_count"] for row in rows)
    result = {
        "status": "frozen_model_czech_full_right_transfer_not_event_truth",
        "source_video_sha256": source_hash,
        "input_sha256": {
            "scan": digest(SCAN),
            "model": digest(MODEL),
            "training": digest(TRAINING),
            "selection": digest(SELECTION),
            "source_reviewed_controls": digest(CONTROLS),
        },
        "feature_code_sha256": digest(ROOT / "prototype/stone_patch_detector.py"),
        "scorer_code_sha256": digest(ROOT / "prototype/cap_patch_verifier.py"),
        "runner_sha256": digest(Path(__file__)),
        "sample_rule": "first, floor-middle and last tracked prefix points; two samples if prefix has two points",
        "model_threshold": 0,
        "proposal_count": len(rows),
        "positive_patch_count_distribution": dict(sorted(counts.items())),
        "source_reviewed_person_controls": [
            {
                "right_proposal_id": pid,
                "any_positive_patch": by_id[pid]["any_positive_patch"],
                "positive_patch_count": by_id[pid]["positive_patch_count"],
            }
            for pid in sorted(control_ids)
        ],
        "rows": rows,
        "limitations": [
            "This is an unchanged-model appearance transfer on an existing candidate inventory, not event detection or independent throw labels.",
            "Only two selected person false-positive paths have source review here; other proposals need source inspection.",
            "A patch score cannot verify a physical delivery, complete track identity, event recall, or game state.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "proposals": len(rows),
                "distribution": result["positive_patch_count_distribution"],
                "controls": result["source_reviewed_person_controls"],
            }
        )
    )


if __name__ == "__main__":
    main()
