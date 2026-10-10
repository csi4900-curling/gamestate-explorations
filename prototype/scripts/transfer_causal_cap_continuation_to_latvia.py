"""Apply unchanged Czech-developed cap continuation to Latvia interval candidates."""

from hashlib import sha256
import json
from math import dist
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from board_onset_probes import onset_frame_detection  # noqa: E402
from causal_cap_continuation import choose_next_cap  # noqa: E402
from local_colour_cap_probe import local_cap_components  # noqa: E402
from scripts.extend_czech_reviewed_stone_caps import search_roi  # noqa: E402
from scripts.probe_czech_reviewed_settle_gaps import sample_indices  # noqa: E402

BASE = ROOT / "validation"
LATVIA = BASE / "throw-event-benchmark/canada-latvia-2024"
PROBE = BASE / "curlobserver-learned-probe"
VIDEO = LATVIA / "source-1080p-1650-2760.mp4"
MOTION = PROBE / "canada-latvia-2024-fixed-grid-motion-merged-frozen-first.json"
BOARDS = PROBE / "canada-latvia-2024-post-event-partial-boards-development.json"
OUT = LATVIA / "board-blind-cap-continuation-transfer-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Latvia cap continuation transfer already exists")
    motion, boards = (json.loads(p.read_text()) for p in (MOTION, BOARDS))
    source_hash = digest(VIDEO)
    if (source_hash != motion["high_resolution_source_sha256"] or
            source_hash != boards["high_resolution_source_sha256"] or
            motion["source_offset_s"] != 1650.0 or
            len(boards["rows"]) != 14):
        raise ValueError("Latvia source, motion or board lineage differs")
    by_motion = {r["candidate_id"]: r for r in motion["rows"]}
    if len(by_motion) != len(motion["rows"]):
        raise ValueError("Duplicate motion candidate")
    video = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                             [cv2.CAP_PROP_N_THREADS, 1])
    fps = video.get(cv2.CAP_PROP_FPS)
    if not video.isOpened() or abs(fps - 30) > 0.01:
        raise ValueError("Latvia source unreadable or FPS changed")
    rows = []
    try:
        for board in boards["rows"]:
            cid = board["candidate_id"]
            path = by_motion[cid]["selection"].get("path", [])
            same = sorted((s for s in board["board"].get("stones", [])
                           if s["colour"] == board["colour"]),
                          key=lambda s: (s["first_seen_s"],
                                         s["local_observation_id"]))
            reason = ("no_two_point_moving_path" if len(path) < 2 else
                      "no_same_colour_stable_board_observation" if not same
                      else None)
            steps = []
            abstention = None
            if reason is None:
                previous, current = path[-2:]
                previous_center = previous["pixel_center"]
                current_center = current["pixel_center"]
                previous_time = previous["source_time_s"]
                current_time = current["source_time_s"]
                offset = motion["source_offset_s"]
                for index in sample_indices(current_time - offset,
                                            same[-1]["first_seen_s"] - offset,
                                            fps)[1:]:
                    time = round(offset + index / fps, 6)
                    ratio = (time - current_time) / (current_time - previous_time)
                    prediction = [current_center[i] +
                                  (current_center[i] - previous_center[i]) * ratio
                                  for i in (0, 1)]
                    roi = search_roi(prediction)
                    video.set(cv2.CAP_PROP_POS_FRAMES, index)
                    ok, frame = video.read()
                    if not ok or frame.shape[:2] != (1080, 1920):
                        raise ValueError(f"Latvia source frame unreadable: {cid} {index}")
                    components = [c for c in local_cap_components(
                        frame, roi, board["colour"])
                        if c["area_px2"] <= 700]
                    decision = choose_next_cap(current_center, previous_center,
                                               ratio, components)
                    steps.append({"source_time_s": time,
                                  "decoded_interval_frame_index": index,
                                  "roi_xyxy_px_1080": list(roi),
                                  "components": components,
                                  "decision": decision})
                    selected = decision["selected"]
                    if selected is None:
                        abstention = decision["status"]
                        break
                    previous_center, current_center = current_center, selected[
                        "centroid_px_1080"]
                    previous_time, current_time = current_time, time
            cap_by_time = {s["source_time_s"]: s["decision"]["selected"][
                "centroid_px_1080"] for s in steps
                if s["decision"]["selected"]}
            board_frames = {f["source_time_s"]: f for f in board["frames"]}
            checkpoints = []
            for observation in same:
                time = observation["first_seen_s"]
                frame = board_frames.get(time)
                if frame is None:
                    raise ValueError(f"Missing first board observation frame: {cid}")
                detected = onset_frame_detection(observation,
                                                 frame["stones"])
                center = cap_by_time.get(time)
                checkpoints.append({
                    "local_observation_id": observation[
                        "local_observation_id"],
                    "first_seen_s": time,
                    "tracked_cap_center_px_1080": center,
                    "internal_board_frame_detection": detected,
                    "tracked_cap_to_onset_detection_px_1080": (
                        round(dist(center, detected["pixel_center_px_1080"]), 3)
                        if center is not None and detected else None),
                    "physical_identity_verified": False,
                })
            rows.append({
                "candidate_id": cid,
                "colour_claim": board["colour"],
                "receiving_view": board["receiving_view"],
                "source_path_last_time_s": path[-1]["source_time_s"]
                if path else None,
                "eligibility_reason": reason,
                "abstention_reason": abstention,
                "same_colour_board_onset_count": len(same),
                "steps": steps,
                "board_onset_checkpoints": checkpoints,
                "physical_throw_verified": False,
                "persistent_stone_identity_verified": False,
                "simulation_ready": False,
            })
    finally:
        video.release()
    result = {
        "status": "unchanged_czech_cap_continuation_latvia_development_transfer_not_event_truth",
        "source_video_sha256": source_hash,
        "source_offset_s": motion["source_offset_s"],
        "input_sha256": {"motion": digest(MOTION), "boards": digest(BOARDS)},
        "runner_sha256": digest(Path(__file__)),
        "selector_code_sha256": digest(ROOT /
                                       "prototype/causal_cap_continuation.py"),
        "component_code_sha256": digest(ROOT /
                                        "prototype/local_colour_cap_probe.py"),
        "onset_code_sha256": digest(ROOT / "prototype/board_onset_probes.py"),
        "method": {
            "source_resolution_px": [1920, 1080],
            "sampling_interval_s": 0.5,
            "source_time_to_frame_index": "round((source_time_s-1650)*30)",
            "search_radius_px": 90,
            "maximum_prediction_error_px": 65,
            "maximum_step_px": 110,
            "maximum_step_growth_vs_previous": 1.8,
            "step_growth_allowance_px": 12,
            "competition_margin_px": 15,
            "competition_distance_ratio": 1.5,
            "maximum_component_area_px2": 700,
            "hsv_masks": "unchanged local_colour_cap_probe thresholds",
            "board_positions_used_for_cap_choice": False,
            "later_board_onsets_used_only_as_horizon_and_diagnostic": True,
        },
        "candidate_count": len(rows),
        "eligible_count": sum(r["eligibility_reason"] is None for r in rows),
        "rows": rows,
        "limitations": [
            "This recording had been exposed in earlier detector development, so this is a cross-recording diagnostic, not an untouched transfer or independent accuracy measurement.",
            "Accepted motion paths and partial boards are provisional same-pipeline observations, not physical throw or stone identities.",
            "The Czech-developed colour and motion thresholds were unchanged, but both matches share a 2024 broadcast style; other camera families remain untested.",
            "Half-second cap associations can switch identity at collisions, cuts or occlusions. Related-pixel board agreement is not metric accuracy.",
            "No event precision/recall, complete game state or simulation-ready trajectory follows.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"candidates": len(rows),
                      "eligible": result["eligible_count"],
                      "abstained": {r["candidate_id"]: r["abstention_reason"]
                                   for r in rows if r["abstention_reason"]},
                      "checkpoints_px": {r["candidate_id"]: [
                          c["tracked_cap_to_onset_detection_px_1080"]
                          for c in r["board_onset_checkpoints"]]
                          for r in rows if r["eligibility_reason"] is None}}))


if __name__ == "__main__":
    main()
