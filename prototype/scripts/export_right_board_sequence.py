"""Compare adjacent partial right-view boards with source-frame alignment checks."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from audit_split_panel_freeze import normalized_split_frame
from right_board_sequence import build_right_board_sequence, USABLE
from right_view_house_alignment import alignment_probe, blue_house_mask


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sample_alignments(video, rows):
    cap = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise ValueError("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    masks = {}
    frames = []
    try:
        for row in rows:
            if row["observation_status"] != USABLE:
                continue
            sample = row["sample_frames"][1]
            time_s = sample["time_s"]
            frame_number = round(time_s * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ok, image = cap.read()
            if not ok:
                raise RuntimeError(f"Could not decode source at {time_s}s")
            image = normalized_split_frame(image)
            masks[row["right_entry_id"]] = blue_house_mask(image)
            frames.append(
                {
                    "right_entry_id": row["right_entry_id"],
                    "sample_time_s": time_s,
                    "decoded_frame_index": frame_number,
                }
            )
    finally:
        cap.release()
    pairs = []
    for before, after in zip(rows, rows[1:]):
        first, second = before["right_entry_id"], after["right_entry_id"]
        item = {"before_right_entry_id": first, "after_right_entry_id": second}
        if first not in masks or second not in masks:
            item["status"] = "abstain_missing_usable_board_sample"
        else:
            try:
                item.update(alignment_probe(masks[first], masks[second]))
                item["status"] = "painted_ring_alignment_probe"
            except ValueError:
                item["status"] = "abstain_empty_painted_house_mask"
        pairs.append(item)
    return frames, pairs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--union", type=Path, required=True)
    parser.add_argument("--right-boards", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    union = json.loads(args.union.read_text())
    boards = json.loads(args.right_boards.read_text())
    if digest(args.video) != union["source_sha256"]:
        parser.error("Source video and candidate fingerprints differ")
    frames, alignments = sample_alignments(args.video, boards["rows"])
    result = build_right_board_sequence(union, boards, alignments)
    result.update(
        {
            "input_sha256": {
                "candidate_review_union": digest(args.union),
                "right_only_partial_caps": digest(args.right_boards),
            },
            "model_code_sha256": digest(ROOT / "prototype/right_board_sequence.py"),
            "alignment_code_sha256": digest(ROOT / "prototype/right_view_house_alignment.py"),
            "cap_set_comparison_code_sha256": digest(ROOT / "prototype/right_view_cap_sequence.py"),
            "frame_normalization_code_sha256": digest(
                ROOT / "prototype/scripts/audit_split_panel_freeze.py"
            ),
            "runner_sha256": digest(Path(__file__)),
            "alignment_sample_frames": frames,
            "alignment_pairs": alignments,
            "transition_status_counts": dict(
                Counter(row["status"] for row in result["transitions"])
            ),
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "transitions": result["transition_count"],
                "statuses": result["transition_status_counts"],
            }
        )
    )


if __name__ == "__main__":
    main()
