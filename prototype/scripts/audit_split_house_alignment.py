"""Audit routed split-view house paint on a five-second source grid."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.split_house_alignment import paint_reference_overlap, sample_status

STEP_S = 5
OVERLAP_THRESHOLD = 0.25


def digest(path):
    value = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def unresolved_groups(rows):
    groups = []
    current = []
    for row in rows:
        if row["status"] == "house_paint_unresolved_review":
            if current and (
                row["run_id"] != current[-1]["run_id"]
                or row["source_time_s"] - current[-1]["source_time_s"] != STEP_S
            ):
                groups.append(current)
                current = []
            current.append(row)
        elif current:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return [
        {
            "run_id": group[0]["run_id"],
            "first_sample_s": group[0]["source_time_s"],
            "last_sample_s": group[-1]["source_time_s"],
            "sample_count": len(group),
            "minimum_overlap": min(row["paint_reference_overlap"] for row in group),
        }
        for group in groups
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument(
        "--reference", nargs=2, action="append", required=True, metavar=("RUN_ID", "REFERENCE_JSON")
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    timeline = json.loads(args.timeline.read_text())
    source_hash = digest(args.video)
    if timeline["source_sha256"] != source_hash:
        parser.error("Video and timeline fingerprints differ")
    runs = {row["id"]: row for row in timeline["supported_runs"] if row["layout"] == "split_2024"}
    references = {}
    for run_id, raw_path in args.reference:
        path = Path(raw_path)
        if run_id in references or run_id not in runs:
            parser.error("Duplicate or unsupported reference run")
        item = json.loads(path.read_text())
        mask_path = path.parent / item["paint_mask_image"]
        if (
            item["source_sha256"] != source_hash
            or item["timeline_sha256"] != digest(args.timeline)
            or item["run_id"] != run_id
            or item["run_interval_s"] != runs[run_id]["interval_s"]
            or item["paint_mask_sha256"] != digest(mask_path)
        ):
            parser.error(f"{run_id} reference lineage differs")
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if mask is None or item["temporal_median_house_ellipse"] is None:
            parser.error(f"{run_id} has no valid house reference")
        references[run_id] = (path, mask)
    if set(references) != set(runs):
        parser.error("Exactly one reference per supported run required")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Unreadable source video")
    rows = []
    try:
        for run_id, run in runs.items():
            start, end = run["interval_s"]
            reference_mask = references[run_id][1]
            for index in range(int((end - start) // STEP_S)):
                t = start + STEP_S * index + STEP_S / 2
                if t >= end:
                    continue
                cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
                ok, frame = cap.read()
                if not ok or frame.shape != (360, 640, 3):
                    raise RuntimeError(f"Cannot decode 640x360 source at {t}")
                score = paint_reference_overlap(frame, reference_mask)
                nearby = [
                    event["id"]
                    for event in timeline["observed_events"]
                    if abs(event["crossing_time_s"] - t) <= STEP_S
                ]
                rows.append(
                    {
                        "run_id": run_id,
                        "source_time_s": t,
                        "paint_reference_overlap": round(score, 4),
                        "status": sample_status(score, threshold=OVERLAP_THRESHOLD),
                        "left_event_ids_within_5s": nearby,
                    }
                )
    finally:
        cap.release()
    counts = dict(Counter(row["status"] for row in rows))
    result = {
        "status": "five_second_right_house_paint_alignment_samples_not_continuous_coverage",
        "source_sha256": source_hash,
        "timeline_sha256": digest(args.timeline),
        "reference_sha256_by_run": {
            run_id: digest(path) for run_id, (path, _) in references.items()
        },
        "feature_code_sha256": digest(ROOT / "prototype/split_house_reference.py"),
        "alignment_code_sha256": digest(ROOT / "prototype/split_house_alignment.py"),
        "runner_sha256": digest(Path(__file__)),
        "sample_step_s": STEP_S,
        "paint_overlap_threshold": OVERLAP_THRESHOLD,
        "sample_count": len(rows),
        "status_counts": counts,
        "unresolved_sample_groups": unresolved_groups(rows),
        "rows": rows,
        "limitations": [
            "Paint absence may be camera cut, occlusion, compression, or detector failure.",
            "Five-second samples cannot establish uninterrupted coverage between samples.",
            "The threshold was selected after exposed nine-frame source probing.",
            "No throw event is accepted, rejected, or re-timed by this alignment audit.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "samples": len(rows),
                "counts": counts,
                "unresolved_groups": result["unresolved_sample_groups"][:12],
            }
        )
    )


if __name__ == "__main__":
    main()
