"""Audit painted-house image alignment at Latvia right-only board samples."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from right_view_house_alignment import ROI_XYXY, alignment_probe, blue_house_mask


def digest(path):
    result = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    observations = json.loads(args.observations.read_text())
    video_hash = digest(args.video)
    if video_hash != observations["source_sha256"]:
        parser.error("Source fingerprints differ")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    masks = {}
    frames = []
    try:
        for row in observations["rows"]:
            if row["observation_status"] != "partial_stable_colour_cap_proposals":
                continue
            time_s = row["sample_frames"][1]["time_s"]
            cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Could not decode source time {time_s}")
            track_id = row["right_raw_track_id"]
            masks[track_id] = blue_house_mask(frame)
            frames.append(
                {
                    "right_raw_track_id": track_id,
                    "sample_time_s": time_s,
                    "decoded_frame_index": round(time_s * fps),
                }
            )
    finally:
        cap.release()
    rows = observations["rows"]
    adjacent = []
    for before, after in zip(rows, rows[1:]):
        a, b = before["right_raw_track_id"], after["right_raw_track_id"]
        item = {"before_right_track_id": a, "after_right_track_id": b}
        if a not in masks or b not in masks:
            item["status"] = "abstain_missing_usable_board_sample"
        else:
            item["status"] = "painted_ring_alignment_probe"
            item.update(alignment_probe(masks[a], masks[b]))
        adjacent.append(item)
    result = {
        "status": "selected_source_only_house_image_alignment_development",
        "source_sha256": video_hash,
        "observations_sha256": digest(args.observations),
        "alignment_code_sha256": digest(ROOT / "prototype/right_view_house_alignment.py"),
        "runner_sha256": digest(Path(__file__)),
        "roi_xyxy": ROI_XYXY,
        "hsv_blue_mask": {"hue_inclusive": [90, 135], "min_saturation": 45, "min_value": 45},
        "translation_search_radius_px": 8,
        "frames": frames,
        "adjacent_pairs": adjacent,
        "limitations": [
            "The ROI and colour mask were chosen after seeing this source; this is development evidence.",
            "People and stones occlude some paint; overlap measures painted pixels, not a camera transform error bound.",
            "One sampled frame per event cannot prove camera pose through the full event interval.",
            "Image alignment does not establish physical stone identity, end identity, or rink coordinates.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "adjacent_probed": sum(
                    row["status"] == "painted_ring_alignment_probe" for row in adjacent
                ),
                "zero_translation_best": sum(
                    row.get("zero_translation_is_best", False) for row in adjacent
                ),
            }
        )
    )


if __name__ == "__main__":
    main()
