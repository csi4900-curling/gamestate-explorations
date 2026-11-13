"""Transfer the frozen side-view stone patch model to reviewed Latvia paths."""

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

BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
VIDEO = BASE / "source-360p.mp4"
QUEUE = BASE / "full-right-variant-review-queue-development.json"
LOW = BASE / "full-right-reviewed-context-transfer-development.json"
HIGH = BASE / "full-right-high-consensus-context-source-audit.json"
HIGH_PACKET = BASE / "full-right-high-consensus-context-source-probe/manifest.json"
MODEL = ROOT / "validation/curlobserver-learned-probe/sideview-patch-transfer-v1/model.npz"
SCANS = {
    "one_second_greedy": BASE / "full-right-area-first-transfer.json",
    "two_second_greedy": BASE / "full-right-area-gap2-development.json",
    "two_second_global": BASE / "full-right-global-area-development.json",
    "two_second_global_later": BASE / "full-right-global-multi-episode-development.json",
}
OUT = BASE / "full-right-reviewed-frozen-sideview-patch-transfer-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def pixel_class(label):
    if label in ("stone_pixels", "moving_stone_body_pixels"):
        return "stone_pixels"
    if label.startswith("person_or_equipment"):
        return "person_or_equipment_pixels"
    if label.startswith("mixed"):
        return "mixed_or_identity_uncertain"
    raise ValueError(f"Unexpected source-pixel class: {label}")


def main():
    queue = json.loads(QUEUE.read_text())
    low = json.loads(LOW.read_text())
    high = json.loads(HIGH.read_text())
    packet = json.loads(HIGH_PACKET.read_text())
    scans = {name: json.loads(path.read_text()) for name, path in SCANS.items()}
    video_hash = digest(VIDEO)
    if (
        queue["source_video_sha256"] != video_hash
        or low["input_sha256"]["queue"] != digest(QUEUE)
        or high["input_sha256"]["queue"] != digest(QUEUE)
        or high["input_sha256"]["source_packet_manifest"] != digest(HIGH_PACKET)
        or any(queue["input_sha256"][name] != digest(path) for name, path in SCANS.items())
    ):
        raise ValueError("Source/review lineage mismatch")
    model = load_model(MODEL)
    if float(model["threshold"]) != 0.0:
        raise ValueError("Frozen model threshold changed")
    labels = {}
    samples_by_id = {}
    for row in low["rows"]:
        pid = row["proposal_id"]
        labels[pid] = pixel_class(row["source_pixel_class"])
        samples_by_id[pid] = row["sample_times_s"]
    high_packet_rows = {row["proposal_id"]: row for row in packet["rows"]}
    for row in high["rows"]:
        pid = row["proposal_id"]
        if pid in labels:
            raise ValueError("Reviewed proposal repeated")
        labels[pid] = pixel_class(row["source_pixel_class"])
        samples_by_id[pid] = high_packet_rows[pid]["sample_times_s"]
    if len(labels) != 53:
        raise ValueError("Expected 53 reviewed proposal prefixes")
    proposal_rows = {}
    raw_tracks = {}
    for name, scan in scans.items():
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
        raise ValueError("Source unreadable")
    rows = []
    try:
        for pid in sorted(labels):
            if pid not in proposal_rows:
                raise ValueError("Reviewed proposal missing from scan")
            variant, track, _ = pid.split(":")
            proposal = proposal_rows[pid]
            points = proposal["observed_prefix_points"]
            if len(points) < 3:
                points = raw_tracks[variant][track]["points"]
            point_by_time = {point["time_s"]: point for point in points}
            if not all(t in point_by_time for t in samples_by_id[pid]):
                raise ValueError(f"Source samples do not match track: {pid}")
            samples = []
            for time in samples_by_id[pid]:
                point = point_by_time[time]
                capture.set(cv2.CAP_PROP_POS_FRAMES, round(time * fps))
                ok, frame = capture.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise ValueError(f"Source decode failed: {pid}")
                result = score_candidates(frame, [{"bbox": point["bbox"]}], model)[0]
                samples.append(
                    {
                        "time_s": time,
                        "patch_score": round(result["patch_score"], 6),
                        "patch_accepted": result["patch_accepted"],
                    }
                )
            rows.append(
                {
                    "proposal_id": pid,
                    "source_pixel_class": labels[pid],
                    "sample_scores": samples,
                    "positive_sample_count": sum(s["patch_accepted"] for s in samples),
                    "any_positive_patch": any(s["patch_accepted"] for s in samples),
                    "physical_throw_verified": False,
                }
            )
    finally:
        capture.release()
    counts = Counter((row["source_pixel_class"], row["any_positive_patch"]) for row in rows)
    result = {
        "status": "frozen_sideview_patch_transfer_on_selected_source_pixels_not_throw_truth",
        "source_video_sha256": video_hash,
        "input_sha256": {
            "queue": digest(QUEUE),
            "low_consensus_review": digest(LOW),
            "high_consensus_review": digest(HIGH),
            "high_consensus_packet": digest(HIGH_PACKET),
            "model": digest(MODEL),
            **{name: digest(path) for name, path in SCANS.items()},
        },
        "feature_code_sha256": digest(ROOT / "prototype/stone_patch_detector.py"),
        "scorer_code_sha256": digest(ROOT / "prototype/cap_patch_verifier.py"),
        "runner_sha256": digest(Path(__file__)),
        "model_threshold": float(model["threshold"]),
        "sample_rule": "The same three source frames and raw track boxes as the prior source-pixel reviews",
        "reviewed_proposal_count": len(rows),
        "counts_by_source_class_and_any_positive_patch": {
            cls: {"positive": counts[cls, True], "negative": counts[cls, False]}
            for cls in ("stone_pixels", "person_or_equipment_pixels", "mixed_or_identity_uncertain")
        },
        "rows": rows,
        "limitations": [
            "The patch model was trained on earlier development broadcasts and has known stone misses; a negative cannot reject a delivery.",
            "The 53 paths are selected postproposal source-pixel reviews, not independent or exhaustive physical throw labels.",
            "A positive stone-like patch can be a handled or displaced stone and cannot confirm a delivery.",
            "Three sampled frames do not establish complete same-stone track identity or event F1.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "proposals": len(rows),
                "counts": result["counts_by_source_class_and_any_positive_patch"],
            }
        )
    )


if __name__ == "__main__":
    main()
