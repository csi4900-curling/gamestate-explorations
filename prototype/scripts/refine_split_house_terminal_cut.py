"""Resolve a sustained no-house-paint tail within a coarse routed run."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.split_house_alignment import paint_reference_overlap, sample_status

TAIL_WINDOW_S = 60
STEP_S = 1
THRESHOLD = .25
MIN_SUSTAINED_LOW_SAMPLES = 5


def digest(path):
    value = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def sustained_tail_start(rows):
    low = 0
    first = None
    for row in reversed(rows):
        if row["status"] != "house_paint_unresolved_review":
            break
        low += 1
        first = row["source_time_s"]
    return first if low >= MIN_SUSTAINED_LOW_SAMPLES else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "timeline", "reference", "alignment", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    timeline = json.loads(args.timeline.read_text())
    reference = json.loads(args.reference.read_text())
    alignment = json.loads(args.alignment.read_text())
    source_hash = digest(args.video)
    run_id = args.run_id
    runs = {row["id"]: row for row in timeline["supported_runs"]
            if row["layout"] == "split_2024"}
    if (run_id not in runs or len({source_hash, timeline["source_sha256"],
                                  reference["source_sha256"], alignment["source_sha256"]}) != 1
            or reference["run_id"] != run_id
            or reference["timeline_sha256"] != digest(args.timeline)
            or alignment["timeline_sha256"] != digest(args.timeline)
            or alignment["reference_sha256_by_run"][run_id] != digest(args.reference)):
        parser.error("Source, timeline, or house-reference lineage differs")
    mask_path = args.reference.parent / reference["paint_mask_image"]
    if digest(mask_path) != reference["paint_mask_sha256"]:
        parser.error("Paint reference mask fingerprint differs")
    mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
    start, end = runs[run_id]["interval_s"]
    first = max(int(start), int(end) - TAIL_WINDOW_S)
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Unreadable source video")
    rows = []
    try:
        for t in range(first, int(end), STEP_S):
            sample_t = t + .5
            cap.set(cv2.CAP_PROP_POS_MSEC, sample_t * 1000)
            ok, frame = cap.read()
            if not ok or frame.shape != (360, 640, 3):
                raise RuntimeError(f"Cannot decode {sample_t}")
            overlap = paint_reference_overlap(frame, mask)
            rows.append({"source_time_s": sample_t,
                         "paint_reference_overlap": round(overlap, 4),
                         "status": sample_status(overlap, threshold=THRESHOLD)})
    finally:
        cap.release()
    cut = sustained_tail_start(rows)
    last_aligned = next((row["source_time_s"] for row in reversed(rows)
                         if row["status"] == "house_paint_aligned_sample"), None)
    near_events = [event["id"] for event in timeline["observed_events"]
                   if cut is not None and cut - 10 <= event["crossing_time_s"] < end]
    result = {
        "status": "source_sampled_terminal_no_house_paint_tail_not_frame_exact_layout_truth",
        "source_sha256": source_hash,
        "timeline_sha256": digest(args.timeline),
        "reference_sha256": digest(args.reference),
        "alignment_sha256": digest(args.alignment),
        "feature_code_sha256": digest(ROOT / "prototype/split_house_alignment.py"),
        "runner_sha256": digest(Path(__file__)),
        "run_id": run_id,
        "run_interval_s": [start, end],
        "sample_interval_s": [first, end],
        "sample_step_s": STEP_S,
        "paint_overlap_threshold": THRESHOLD,
        "minimum_sustained_low_samples": MIN_SUSTAINED_LOW_SAMPLES,
        "last_aligned_sample_s": last_aligned,
        "first_sustained_low_sample_s": cut,
        "provisional_left_event_ids_at_or_after_cut_minus_10s": near_events,
        "rows": rows,
        "limitations": [
            "The camera transition falls between sampled instants; no frame-exact cut is claimed.",
            "Low house-paint overlap can also arise from occlusion, so source-frame review is required.",
            "No provisional throw candidate or existing router timeline is changed by this audit.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"run": run_id, "last_aligned": last_aligned,
                      "first_sustained_low": cut,
                      "near_left_events": near_events}))


if __name__ == "__main__":
    main()
