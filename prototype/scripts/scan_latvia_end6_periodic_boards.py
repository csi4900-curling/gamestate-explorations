"""Periodic partial right-house observations inside Latvia's end-6 blind span.

This source-derived sequence may prioritize review of missing event windows;
it does not infer that any cap difference is a delivered or removed stone.
"""

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
from probe_static_left_right_cap_motion import right_colour_proposals
from right_view_partial_board import stable_cap_candidates
from right_view_house_alignment import alignment_probe, blue_house_mask
from right_view_cap_sequence import compare_cap_sets

VIDEO = ROOT / "validation/throw-event-benchmark/canada-latvia-2024/source-360p.mp4"
SCAN = (
    ROOT
    / "validation/throw-event-benchmark/canada-latvia-2024/end-marker-full-2d-local-development.json"
)
HANDOFF = (
    ROOT
    / "validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1/full-match-candidate-partial-state-handoff.json"
)
OUT = (
    ROOT
    / "validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1/end6-periodic-right-board-development.json"
)
WINDOW_STEP_S = 10
SAMPLE_OFFSETS_S = (0, 2, 4)
SCENE_MAE_MAX = 20
HOUSE_BLUE_IOU_MIN = 0.7


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def observe_window(capture, fps, anchor_s):
    frames, patches = [], []
    middle_mask = None
    for offset in SAMPLE_OFFSETS_S:
        time_s = anchor_s + offset
        capture.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
        ok, frame = capture.read()
        if not ok or frame.shape[:2] != (360, 640):
            raise RuntimeError(f"Could not decode source time {time_s}")
        patches.append(frame[155:245, 330:630].astype(np.int16))
        if offset == SAMPLE_OFFSETS_S[1]:
            middle_mask = blue_house_mask(frame)
        proposals = right_colour_proposals(frame)
        coloured = [
            {"colour": colour, **row}
            for colour, items in proposals.items()
            for row in items
            if 360 <= row["pixel"][0] <= 615
            and 155 <= row["pixel"][1] <= 235
            and row["cap_area_px2"] >= 6
        ]
        frames.append({"time_s": time_s, "cap_candidates": coloured})
    maes = [round(float(np.mean(np.abs(a - b))), 3) for a, b in zip(patches, patches[1:])]
    if max(maes) >= SCENE_MAE_MAX:
        status, stable = "abstain_scene_or_player_motion", []
    else:
        stable = stable_cap_candidates(frames)
        status = (
            "partial_stable_colour_cap_proposals" if stable else "no_stable_colour_cap_proposals"
        )
    return {
        "anchor_time_s": anchor_s,
        "sample_frames": frames,
        "scene_mae_between_samples": maes,
        "observation_status": status,
        "stable_cap_proposals": stable,
        "complete_board_verified": False,
        "simulation_ready": False,
    }, middle_mask


def main():
    if OUT.exists():
        raise SystemExit("Output exists; preserve previous scan")
    scan = json.loads(SCAN.read_text())
    handoff = json.loads(HANDOFF.read_text())
    source_hash = digest(VIDEO)
    if source_hash != scan["video_sha256"] or source_hash != handoff["source_sha256"]:
        raise ValueError("Source provenance differs")
    end6 = [row["time_s"] for row in scan["samples"] if row["marker"] and row["marker"]["end"] == 6]
    if len(end6) < 2:
        raise ValueError("No repeated displayed end 6")
    start = end6[0]
    blind = handoff["left_trigger_blind_intervals"]
    if len(blind) != 1 or not blind[0]["interval_s"][0] < start < blind[0]["interval_s"][1]:
        raise ValueError("End-6 display and blind source interval differ")
    stop = blind[0]["interval_s"][1]
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows, masks = [], []
    for time_s in range(start, stop - SAMPLE_OFFSETS_S[-1], WINDOW_STEP_S):
        row, mask = observe_window(capture, fps, time_s)
        rows.append(row)
        masks.append(mask)
    capture.release()
    transitions = []
    for before, after, old_mask, new_mask in zip(rows, rows[1:], masks, masks[1:]):
        item = {
            "before_anchor_s": before["anchor_time_s"],
            "after_anchor_s": after["anchor_time_s"],
            "physical_board_change_verified": False,
            "physical_throw_verified": False,
            "simulation_ready": False,
        }
        if (
            before["observation_status"] != "partial_stable_colour_cap_proposals"
            or after["observation_status"] != "partial_stable_colour_cap_proposals"
        ):
            item["status"] = "abstain_missing_usable_cap_set"
        else:
            alignment = alignment_probe(old_mask, new_mask)
            item["painted_house_alignment"] = alignment
            if (
                not alignment["zero_translation_is_best"]
                or alignment["best_translation_second_to_first_px"] != [0, 0]
                or alignment["best_mask_iou"] < HOUSE_BLUE_IOU_MIN
            ):
                item["status"] = "abstain_house_alignment"
            else:
                item["status"] = "conditional_image_cap_comparison"
                item.update(
                    compare_cap_sets(before["stable_cap_proposals"], after["stable_cap_proposals"])
                )
        transitions.append(item)
    result = {
        "status": "periodic_partial_right_image_board_not_game_state_or_throw_truth",
        "source_sha256": source_hash,
        "marker_scan_sha256": digest(SCAN),
        "handoff_sha256": digest(HANDOFF),
        "proposal_code_sha256": digest(
            ROOT / "prototype/scripts/probe_static_left_right_cap_motion.py"
        ),
        "stable_cap_code_sha256": digest(ROOT / "prototype/right_view_partial_board.py"),
        "house_alignment_code_sha256": digest(ROOT / "prototype/right_view_house_alignment.py"),
        "cap_comparison_code_sha256": digest(ROOT / "prototype/right_view_cap_sequence.py"),
        "runner_sha256": digest(Path(__file__)),
        "interval_s": [start, stop],
        "window_step_s": WINDOW_STEP_S,
        "sample_offsets_s": SAMPLE_OFFSETS_S,
        "scene_mae_max": SCENE_MAE_MAX,
        "minimum_painted_house_blue_iou": HOUSE_BLUE_IOU_MIN,
        "observation_status_counts": dict(Counter(row["observation_status"] for row in rows)),
        "transition_status_counts": dict(Counter(row["status"] for row in transitions)),
        "windows": rows,
        "adjacent_transitions": transitions,
        "limitations": [
            "Stable colour blobs can be hats, clothing, equipment, occluded or handled stones.",
            "Adjacent image differences do not identify stone births, removals, collisions or throws.",
            "The painted-ring check samples two frames and is not a full camera-pose calibration.",
            "Ten-second windows can miss fast events and cannot establish release or settle time.",
            "Thresholds were developed on exposed footage, so this is not independent validation.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "windows": len(rows),
                "observations": result["observation_status_counts"],
                "transitions": result["transition_status_counts"],
            }
        )
    )


if __name__ == "__main__":
    main()
