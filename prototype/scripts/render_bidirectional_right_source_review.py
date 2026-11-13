"""Render all newly covered and off-reference bidirectional right proposals."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np


def digest(path):
    result = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def matching_window_ids(proposal, reference):
    return [
        event["id"]
        for event in reference["events"]
        if event["colour"] == proposal["colour_claim"]
        and event["delivery_interval_s"][0]
        <= proposal["passage"]["time_s"]
        <= event["delivery_interval_s"][1]
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "probe", "reference", "output_dir"):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists")
    probe = json.loads(args.probe.read_text())
    reference = json.loads(args.reference.read_text())
    source_hash = digest(args.video)
    if (
        probe["source_sha256"] != source_hash
        or reference["source_sha256"] != source_hash
        or probe["coarse_reference_sha256"] != digest(args.reference)
    ):
        parser.error("Source or coarse-reference fingerprints differ")
    new_windows = set(probe["newly_covered_coarse_window_ids"])
    selected = []
    for proposal in probe["directional_review_proposals"]:
        ids = matching_window_ids(proposal, reference)
        if not ids or new_windows.intersection(ids):
            selected.append((proposal, ids))
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    args.output_dir.mkdir(parents=True)
    sheets, rows = [], []
    try:
        for start in range(0, len(selected), 5):
            group = selected[start : start + 5]
            sheet = np.full((230 * len(group), 960, 3), 20, dtype=np.uint8)
            for i, (proposal, window_ids) in enumerate(group):
                points = proposal["observed_prefix_points"]
                passage_t = proposal["passage"]["time_s"]
                chosen = [
                    points[0],
                    min(points, key=lambda point: abs(point["time_s"] - passage_t)),
                    points[-1],
                ]
                samples = []
                for col, point in enumerate(chosen):
                    t = point["time_s"]
                    frame_index = round(t * fps)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                    ok, frame = cap.read()
                    if not ok or frame.shape[:2] != (360, 640):
                        raise RuntimeError(f"Could not decode source second {t}")
                    crop = frame[120:330, 320:640].copy()
                    x, y = point["pixel"]
                    cv2.circle(crop, (round(x - 320), round(y - 120)), 8, (0, 255, 0), 2)
                    top, left = i * 230, col * 320
                    sheet[top + 20 : top + 230, left : left + 320] = crop
                    cv2.putText(
                        sheet,
                        f"{proposal['raw_track_id']} {t:.1f}s",
                        (left + 5, top + 16),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.44,
                        (255, 255, 255),
                        1,
                    )
                    samples.append(
                        {
                            "source_time_s": t,
                            "decoded_frame_index": frame_index,
                            "tracked_pixel": point["pixel"],
                        }
                    )
                rows.append(
                    {
                        "raw_track_id": proposal["raw_track_id"],
                        "direction": proposal["direction"],
                        "coarse_window_ids": window_ids,
                        "selection_reason": (
                            "new_coarse_window" if window_ids else "outside_all_coarse_windows"
                        ),
                        "sheet": f"sheet-{start // 5 + 1:02}.jpg",
                        "samples": samples,
                    }
                )
            path = args.output_dir / f"sheet-{start // 5 + 1:02}.jpg"
            if not cv2.imwrite(str(path), sheet):
                raise RuntimeError(f"Could not write {path}")
            sheets.append(
                {
                    "file": path.name,
                    "sha256": digest(path),
                    "raw_track_ids": [proposal["raw_track_id"] for proposal, _ in group],
                }
            )
    finally:
        cap.release()
    result = {
        "status": "selected_development_source_strips_not_independent_throw_labels",
        "source_sha256": source_hash,
        "probe_sha256": digest(args.probe),
        "coarse_reference_sha256": digest(args.reference),
        "runner_sha256": digest(Path(__file__)),
        "selection_rule": "Every bidirectional proposal in a newly covered coarse window, plus every proposal outside all same-colour coarse windows.",
        "rows": rows,
        "sheets": sheets,
        "limitations": [
            "This is development-agent review of proposals chosen after seeing coarse windows.",
            "Three sampled frames can show a moving object but not prove a complete physical delivery.",
        ],
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"selected": len(rows), "sheets": len(sheets)}))


if __name__ == "__main__":
    main()
