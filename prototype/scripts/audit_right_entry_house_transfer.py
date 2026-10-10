"""Transfer the Latvia painted-house alignment gate to another right-entry ledger."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from right_view_house_alignment import (ROI_XYXY, alignment_probe,
                                        blue_house_mask)


def digest(path):
    result = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--entries", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    entries = json.loads(args.entries.read_text())
    source_hash = digest(args.video)
    if entries["source_sha256"] != source_hash:
        parser.error("Source fingerprints differ")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration_s = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
    frames = []
    masks = []
    try:
        for entry in entries["entry_review_proposals"]:
            time_s = entry["entry_crossing"]["time_s"] + 20
            if time_s >= duration_s:
                raise ValueError("Sample beyond source duration")
            frame_index = round(time_s * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Cannot decode frame {frame_index}")
            mask = blue_house_mask(frame)
            masks.append(mask)
            frames.append({"right_raw_track_id": entry["raw_track_id"],
                           "entry_time_s": entry["entry_crossing"]["time_s"],
                           "sample_time_s": round(time_s, 3),
                           "decoded_frame_index": frame_index,
                           "blue_house_mask_px": int(mask.sum())})
    finally:
        cap.release()
    pairs = []
    for before, after, a, b in zip(frames, frames[1:], masks, masks[1:]):
        probe = alignment_probe(a, b)
        pairs.append({
            "before_right_track_id": before["right_raw_track_id"],
            "after_right_track_id": after["right_raw_track_id"],
            "sample_interval_s": [before["sample_time_s"], after["sample_time_s"]],
            **probe,
            "latvia_gate_passes": bool(
                probe["zero_translation_is_best"] and
                probe["best_translation_second_to_first_px"] == [0, 0] and
                probe["best_mask_iou"] >= 0.7),
        })
    output = {
        "status": "source_only_painted_house_transfer_not_board_or_event_validation",
        "source_sha256": source_hash,
        "entries_sha256": digest(args.entries),
        "alignment_code_sha256": digest(ROOT / "prototype/right_view_house_alignment.py"),
        "runner_sha256": digest(Path(__file__)),
        "sample_offset_after_entry_s": 20,
        "blue_house_roi_xyxy": ROI_XYXY,
        "latvia_development_gate": "zero best shift within 8px and blue-mask IoU >= 0.7",
        "sample_count": len(frames),
        "adjacent_pair_count": len(pairs),
        "gate_counts": dict(Counter("pass" if row["latvia_gate_passes"] else "abstain"
                                    for row in pairs)),
        "frames": frames,
        "adjacent_pairs": pairs,
        "limitations": [
            "Entries are exposed detector proposals, not independently verified throws.",
            "Pairs may cross physical end or broadcast phase boundaries; no stone association is attempted.",
            "The sample is only one frame 20 seconds after each proposed entry.",
            "The blue mask and 0.7 gate were developed on Latvia; this Czech replay is a transfer diagnostic, not an accuracy benchmark.",
            "Occlusion can lower mask IoU even when the camera is geometrically stable.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"frames": len(frames), "pairs": len(pairs),
                      "gate_counts": output["gate_counts"]}))


if __name__ == "__main__":
    main()
