"""Probe source pixels below the right detector ROI for matched camera seams."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from right_backward_seam import backward_extension
from expanded_right_colour import expanded_right_colour_proposals


def digest(path):
    result = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--windows", type=Path, required=True)
    parser.add_argument("--right-proposals", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    windows = json.loads(args.windows.read_text())
    right = json.loads(args.right_proposals.read_text())
    video_hash = digest(args.video)
    if (
        video_hash != windows["source_sha256"]
        or video_hash != right["source_sha256"]
        or digest(args.right_proposals) != windows["input_sha256"]["right_proposals"]
    ):
        parser.error("Video, windows and right-proposal sources disagree")
    proposals = {item["raw_track_id"]: item for item in right["entry_review_proposals"]}
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Could not open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    cache = {}

    def source_proposals(time_s, colour):
        if time_s not in cache:
            cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Could not decode source at {time_s}s")
            cache[time_s] = expanded_right_colour_proposals(frame)
        return cache[time_s][colour]

    rows = []
    try:
        for row in windows["rows"]:
            if row["unobserved_camera_seam_s"] is None:
                continue
            raw_id = row["candidate_id"]
            proposal = proposals[row["right_raw_track_id"]]
            if (
                proposal["colour_claim"] != row["colour_claim"]
                or proposal["observed_prefix_interval_s"] != row["right_observed_prefix_interval_s"]
            ):
                raise ValueError(f"Right prefix disagrees: {raw_id}")
            first = proposal["observed_prefix_points"][0]
            extension = backward_extension(
                first,
                row["left_observed_track_interval_s"][1],
                row["colour_claim"],
                source_proposals,
            )
            new_start = extension["new_first_observed_s"]
            left_end = row["left_observed_track_interval_s"][1]
            rows.append(
                {
                    "candidate_id": raw_id,
                    "right_raw_track_id": proposal["raw_track_id"],
                    "colour_claim": row["colour_claim"],
                    "original_unobserved_seam_s": row["unobserved_camera_seam_s"],
                    "conditional_extended_right_first_s": new_start,
                    "conditional_remaining_seam_s": [left_end, new_start],
                    "conditional_remaining_seam_duration_s": round(new_start - left_end, 3),
                    **extension,
                }
            )
    finally:
        cap.release()
    output = {
        "status": "source_pixel_right_backward_extension_diagnostic_not_physical_identity",
        "source_sha256": video_hash,
        "input_sha256": {
            "windows": digest(args.windows),
            "right_proposals": digest(args.right_proposals),
        },
        "expanded_detector_code_sha256": digest(ROOT / "prototype/expanded_right_colour.py"),
        "extension_code_sha256": digest(ROOT / "prototype/right_backward_seam.py"),
        "runner_sha256": digest(Path(__file__)),
        "expanded_right_roi_xyxy": [330, 145, 630, 360],
        "expanded_colour_area_px2": [4, 220],
        "conditional_two_view_rows": len(rows),
        "rows_with_added_source_observations": sum(bool(row["added_observations"]) for row in rows),
        "stop_reason_counts": dict(Counter(row["stop_reason"] for row in rows)),
        "rows": rows,
        "limitations": [
            "Expanded ROI and area ceiling were chosen after viewing exposed Scotland seams.",
            "Backward colour association is conditional and may switch among same-colour objects.",
            "A source-pixel observation is not a physical release, settle or verified cross-camera identity.",
            "These positive-selected seams do not measure detector recall or precision.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "two_view": len(rows),
                "extended": output["rows_with_added_source_observations"],
                "stop_reasons": output["stop_reason_counts"],
            }
        )
    )


if __name__ == "__main__":
    main()
