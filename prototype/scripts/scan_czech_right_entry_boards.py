"""Transfer the fixed right-view cap sampler to the full Czechia recording."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from right_view_partial_board import stable_cap_candidates
from probe_static_left_right_cap_motion import right_colour_proposals
from scan_scotland_right_entry_boards import eligible_tail, OFFSETS_S, NEXT_ENTRY_GUARD_S


def digest(path):
    value = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "fusion", "source_review", "output"):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    fusion = json.loads(args.fusion.read_text())
    source_review = json.loads(args.source_review.read_text())
    source_hash = digest(args.video)
    if source_hash != fusion["source_sha256"] or source_hash != source_review["source_sha256"]:
        parser.error("Source fingerprints differ")
    if fusion["right_sha256"] != source_review["variant_sha256"]:
        parser.error("Fusion and source review use different right proposals")
    entries = sorted(fusion["right_entries"], key=lambda row: row["right_entry_time_s"])
    reviewed = {row["raw_track_id"]: row for row in source_review["review"]}
    if (len(reviewed) != len(source_review["review"])
            or set(reviewed) != {row["right_raw_track_id"] for row in entries}):
        parser.error("Source review must cover the exact right-entry set")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Unreadable source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
    rows = []
    try:
        for index, entry in enumerate(entries):
            entry_time = entry["right_entry_time_s"]
            next_time = (entries[index + 1]["right_entry_time_s"]
                         if index + 1 < len(entries) else None)
            abstention = eligible_tail(entry_time, next_time, duration)
            frames, patches, stable, maes = [], [], [], []
            if abstention is None:
                for offset in OFFSETS_S:
                    t = entry_time + offset
                    cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
                    ok, image = cap.read()
                    if not ok or image.shape[:2] != (360, 640):
                        raise RuntimeError(f"Could not decode 640x360 source at {t}")
                    patches.append(image[155:245, 330:630].astype(np.int16))
                    proposals = right_colour_proposals(image)
                    coloured = [{"colour": colour, **item}
                                for colour, items in proposals.items() for item in items
                                if 360 <= item["pixel"][0] <= 615
                                and 155 <= item["pixel"][1] <= 235
                                and item["cap_area_px2"] >= 6]
                    frames.append({"time_s": round(t, 3), "cap_candidates": coloured})
                maes = [round(float(np.mean(np.abs(a - b))), 3)
                        for a, b in zip(patches, patches[1:])]
                if max(maes) >= 20:
                    abstention = "abstain_scene_or_player_motion"
                else:
                    stable = stable_cap_candidates(frames)
            status = abstention or ("partial_stable_colour_cap_proposals" if stable else
                                    "no_stable_colour_cap_proposals")
            rows.append({
                "right_raw_track_id": entry["right_raw_track_id"],
                "conditional_left_candidate_id": entry["conditional_left_candidate_id"],
                "source_reviewed_prefix_class": reviewed[entry["right_raw_track_id"]][
                    "sampled_prefix_class"],
                "entry_time_s": entry_time,
                "next_right_entry_time_s": next_time,
                "observation_status": status,
                "scene_mae_between_samples": maes,
                "sample_frames": frames,
                "stable_cap_proposals": stable,
                "stable_cap_colour_counts": dict(Counter(x["colour"] for x in stable)),
                "coordinate_frame": "full_source_right_camera_pixels_not_metric",
                "complete_board_verified": False,
                "physical_settle_verified": False,
                "persistent_stone_identity_verified": False,
                "simulation_ready": False,
            })
    finally:
        cap.release()
    result = {
        "status": "czech_right_entry_partial_cap_transfer_not_physical_board_state",
        "source_sha256": source_hash,
        "fusion_sha256": digest(args.fusion),
        "source_review_sha256": digest(args.source_review),
        "proposal_code_sha256": digest(ROOT / "prototype/scripts/probe_static_left_right_cap_motion.py"),
        "stable_cap_code_sha256": digest(ROOT / "prototype/right_view_partial_board.py"),
        "tail_rule_code_sha256": digest(ROOT / "prototype/scripts/scan_scotland_right_entry_boards.py"),
        "runner_sha256": digest(Path(__file__)),
        "sample_offsets_after_entry_s": list(OFFSETS_S),
        "next_entry_guard_s": NEXT_ENTRY_GUARD_S,
        "candidate_roi_xyxy": [360, 155, 615, 235],
        "scene_comparison_roi_xyxy": [330, 155, 630, 245],
        "max_scene_mae_for_observation": 20,
        "max_stable_cap_displacement_px": 5,
        "observation_status_counts": dict(Counter(row["observation_status"] for row in rows)),
        "stable_cap_proposal_count": sum(len(row["stable_cap_proposals"]) for row in rows),
        "rows": rows,
        "limitations": [
            "This applies the previously selected right-view sampler without tuning on Czechia.",
            "The source-review classes are development-agent observations of short prefixes, not independent throw labels.",
            "Stable cap blobs can be nonstones and do not establish complete settled boards or physical stone identity.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"rows": len(rows), "statuses": result["observation_status_counts"],
                      "stable_caps": result["stable_cap_proposal_count"]}))


if __name__ == "__main__":
    main()
