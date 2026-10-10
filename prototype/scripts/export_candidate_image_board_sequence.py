"""Audit adjacent candidate board images on their common right-view samples."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from audit_split_panel_freeze import normalized_split_frame
from candidate_image_board_sequence import USABLE, compare_candidate_boards
from right_view_house_alignment import alignment_probe, blue_house_mask


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sample_alignments(video, rows):
    cap = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise ValueError("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    masks = {}
    frames = []
    try:
        for row in rows:
            observation = row["post_candidate_image_observation"]
            if observation["status"] != USABLE:
                continue
            times = observation["sample_times_s"]
            if len(times) != 3:
                raise ValueError("Usable observation requires three sample frames")
            t = times[1]
            frame_number = round(t * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Could not decode source at {t}s")
            masks[row["candidate_id"]] = blue_house_mask(normalized_split_frame(frame))
            frames.append({"candidate_id": row["candidate_id"],
                           "sample_time_s": t,
                           "decoded_frame_index": frame_number})
    finally:
        cap.release()
    pairs = []
    for before, after in zip(rows, rows[1:]):
        a, b = before["candidate_id"], after["candidate_id"]
        item = {"before_candidate_id": a, "after_candidate_id": b}
        if a not in masks or b not in masks:
            item["status"] = "abstain_missing_usable_board_sample"
        else:
            try:
                item.update(alignment_probe(masks[a], masks[b]))
                item["status"] = "painted_ring_alignment_probe"
            except ValueError:
                item["status"] = "abstain_empty_painted_house_mask"
        pairs.append(item)
    return frames, pairs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    handoff = json.loads(args.handoff.read_text())
    if digest(args.video) != handoff["source_sha256"]:
        parser.error("Source video and handoff differ")
    frames, alignment = sample_alignments(args.video, handoff["ordered_candidates"])
    result = compare_candidate_boards(handoff, alignment)
    result.update({
        "handoff_sha256": digest(args.handoff),
        "model_code_sha256": digest(ROOT / "prototype/candidate_image_board_sequence.py"),
        "alignment_code_sha256": digest(ROOT / "prototype/right_view_house_alignment.py"),
        "cap_set_comparison_code_sha256": digest(ROOT / "prototype/right_view_cap_sequence.py"),
        "frame_normalization_code_sha256": digest(
            ROOT / "prototype/scripts/audit_split_panel_freeze.py"),
        "runner_sha256": digest(Path(__file__)),
        "alignment_sample_frames": frames,
        "alignment_pairs": alignment,
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"candidates": result["candidate_count"],
                      "statuses": result["transition_status_counts"]}))


if __name__ == "__main__":
    main()
