"""Export partial right-view cap observations after right-only review entries."""

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
from right_view_cap_sequence import compare_cap_sets
from probe_static_left_right_cap_motion import right_colour_proposals
from audit_split_panel_freeze import normalized_split_frame


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def observe_anchor(cap, fps, duration, anchor_s):
    frames, image_patches = [], []
    for offset in (15, 20, 25):
        t = anchor_s + offset
        if t >= duration:
            return {"anchor_time_s": anchor_s,
                    "observation_status": "abstain_insufficient_tail_video",
                    "scene_mae_between_samples": [], "sample_frames": [],
                    "stable_cap_proposals": []}
        cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
        ok, image = cap.read()
        if not ok:
            raise RuntimeError(f"Could not decode source {t}")
        image = normalized_split_frame(image)
        image_patches.append(image[155:245, 330:630].astype(np.int16))
        proposals = right_colour_proposals(image)
        coloured = [{"colour": colour, **row}
                    for colour, items in proposals.items() for row in items
                    if 360 <= row["pixel"][0] <= 615 and
                    155 <= row["pixel"][1] <= 235 and
                    row["cap_area_px2"] >= 6]
        frames.append({"time_s": round(t, 3), "cap_candidates": coloured})
    maes = [round(float(np.mean(np.abs(a - b))), 3)
            for a, b in zip(image_patches, image_patches[1:])]
    if max(maes) >= 20:
        status, stable = "abstain_scene_or_player_motion", []
    else:
        stable = stable_cap_candidates(frames)
        status = ("partial_stable_colour_cap_proposals" if stable
                  else "no_stable_colour_cap_proposals")
    return {"anchor_time_s": anchor_s, "observation_status": status,
            "scene_mae_between_samples": maes,
            "sample_frames": frames, "stable_cap_proposals": stable}


def anchors_agree(observations, central):
    """Require the same status and a complete unique cap match at each anchor."""
    status = central["observation_status"]
    if any(row["observation_status"] != status for row in observations):
        return False
    if status != "partial_stable_colour_cap_proposals":
        return True
    reference = central["stable_cap_proposals"]
    for row in observations:
        other = row["stable_cap_proposals"]
        comparison = compare_cap_sets(reference, other)
        if len(reference) != len(other) or len(comparison["matched_local_caps"]) != len(reference):
            return False
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--fusion", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    fusion = json.loads(args.fusion.read_text())
    video_hash = digest(args.video)
    if fusion["source_sha256"] != video_hash:
        parser.error("Source fingerprints differ")
    entries = [row for row in fusion["right_entries"]
               if row["fusion_status"].startswith("right_only_")]
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Unreadable video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
    rows = []
    try:
        for entry in entries:
            bracket = entry.get("right_entry_bracket_s")
            current = entry["right_entry_time_s"]
            if bracket is not None and not (len(bracket) == 2 and
                                             bracket[0] <= current <= bracket[1]):
                raise ValueError(f"Invalid entry crossing bracket for {entry['right_raw_track_id']}")
            anchors = sorted(set([current] + (bracket or [])))
            observations = [observe_anchor(cap, fps, duration, anchor)
                            for anchor in anchors]
            central = next(row for row in observations if row["anchor_time_s"] == current)
            robust = anchors_agree(observations, central)
            status = (central["observation_status"] if robust else
                      "abstain_entry_time_sensitive")
            stable = central["stable_cap_proposals"] if robust else []
            rows.append({
                "right_entry_id": entry.get("right_entry_id", entry["right_raw_track_id"]),
                "right_raw_track_id": entry["right_raw_track_id"],
                "entry_time_s": current,
                "entry_time_bracket_s": bracket,
                "entry_fusion_status": entry["fusion_status"],
                "observation_status": status,
                "scene_mae_between_samples": central["scene_mae_between_samples"],
                "sample_frames": central["sample_frames"],
                "stable_cap_proposals": stable,
                "anchor_observations": observations,
                "anchor_stability_agreement": robust if len(observations) > 1 else None,
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
        "status": "right_only_postentry_partial_colour_cap_observations_not_game_state",
        "source_sha256": video_hash,
        "fusion_sha256": digest(args.fusion),
        "proposal_code_sha256": digest(ROOT / "prototype/scripts/probe_static_left_right_cap_motion.py"),
        "frame_normalization_code_sha256": digest(
            ROOT / "prototype/scripts/audit_split_panel_freeze.py"),
        "stable_cap_code_sha256": digest(ROOT / "prototype/right_view_partial_board.py"),
        "cap_set_comparison_code_sha256": digest(ROOT / "prototype/right_view_cap_sequence.py"),
        "runner_sha256": digest(Path(__file__)),
        "sample_offsets_after_entry_s": [15, 20, 25],
        "candidate_roi_xyxy": [360, 155, 615, 235],
        "scene_comparison_roi_xyxy": [330, 155, 630, 245],
        "max_scene_mae_for_observation": 20,
        "max_stable_cap_displacement_px": 5,
        "observation_status_counts": dict(Counter(row["observation_status"] for row in rows)),
        "rows": rows,
        "limitations": [
            "Colour-cap blobs can represent nonstones; source-frame review is required.",
            "A stable cap proposal is not a complete board or persistent stone identity.",
            "Large scene MAE can come from people even if the camera itself is fixed.",
            "Sampling 15–25 seconds after an image entry does not prove physical settle time.",
            "Entry-time brackets can change the sampled scene; disagreement forces abstention.",
            "ROI and thresholds were chosen after source inspection on this exposed recording.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"rows": len(rows), "statuses": result["observation_status_counts"]}))


if __name__ == "__main__":
    main()
