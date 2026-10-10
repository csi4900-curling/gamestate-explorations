"""Probe board-blind cap continuation across reviewed Czech settle gaps."""

from hashlib import sha256
import json
from math import dist
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from causal_cap_continuation import choose_next_cap  # noqa: E402
from local_colour_cap_probe import local_cap_components  # noqa: E402

BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
VIDEO = BASE / "source-1080p-full-format270.mp4"
GAPS = BASE / "full-reviewed-stone-replay-gaps-development.json"
INVENTORY = BASE / "full-reviewed-settle-gap-cap-inventory-development.json"
OUT = BASE / "full-reviewed-stone-cap-continuations-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def search_roi(prediction, shape=(1080, 1920), radius=90):
    height, width = shape
    x, y = prediction
    return (max(0, int(x - radius)), max(0, int(y - radius)),
            min(width, int(x + radius + 1)),
            min(height, int(y + radius + 1)))


def main():
    if OUT.exists():
        raise ValueError("Cap-continuation artifact already exists")
    gaps = json.loads(GAPS.read_text())
    inventory = json.loads(INVENTORY.read_text())
    source_hash = digest(VIDEO)
    if source_hash != inventory["source_video_sha256"]:
        raise ValueError("Inventory and source video differ")
    by_gap = {r["episode_id"]: r for r in gaps["rows"]}
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened() or abs(fps - 30) > 0.01:
        raise ValueError("Source unreadable or FPS changed")
    rows = []
    try:
        for case in inventory["rows"]:
            gap = by_gap[case["episode_id"]]
            path = gap["observed_left_motion_path"]
            if len(path) < 2:
                raise ValueError("Continuation requires two observed path positions")
            previous, current = path[-2:]
            previous_center = previous["pixel_center_1080"]
            current_center = current["pixel_center_1080"]
            previous_time = previous["source_time_s"]
            current_time = current["source_time_s"]
            steps = []
            abstention = None
            for sample in case["samples"][1:]:
                time = sample["source_time_s"]
                dt_ratio = (time - current_time) / (current_time - previous_time)
                prediction = [current_center[i] +
                              (current_center[i] - previous_center[i]) * dt_ratio
                              for i in (0, 1)]
                roi = search_roi(prediction)
                cap.set(cv2.CAP_PROP_POS_FRAMES, sample["decoded_frame_index"])
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (1080, 1920):
                    raise ValueError("Source frame unreadable")
                components = [c for c in local_cap_components(
                    frame, roi, case["colour_claim"])
                    if c["area_px2"] <= 700]
                decision = choose_next_cap(current_center, previous_center,
                                           dt_ratio, components)
                selected = decision["selected"]
                near_competitors = (sum(
                    dist(c["centroid_px_1080"],
                         selected["centroid_px_1080"]) <= 65
                    for c in components if c is not selected)
                    if selected else None)
                steps.append({
                    "source_time_s": time,
                    "decoded_frame_index": sample["decoded_frame_index"],
                    "roi_xyxy_px_1080": list(roi),
                    "component_count_in_roi": len(components),
                    "components": components,
                    "decision": decision,
                    "other_same_colour_components_within_65px": near_competitors,
                })
                if selected is None:
                    abstention = decision["status"]
                    break
                previous_center, current_center = current_center, selected[
                    "centroid_px_1080"]
                previous_time, current_time = current_time, time
            reached = (bool(steps) and abstention is None and
                       steps[-1]["source_time_s"] ==
                       case["first_same_colour_board_time_s"])
            board_distance = (min(dist(current_center, center) for center in
                                  case["first_same_colour_board_centers_px_1080"])
                              if reached else None)
            rows.append({
                "episode_id": case["episode_id"],
                "left_motion_candidate_id": case["left_motion_candidate_id"],
                "colour_claim": case["colour_claim"],
                "initial_observed_path_points": [previous, current],
                "evaluation_horizon_first_board_time_s": case[
                    "first_same_colour_board_time_s"],
                "board_blind_continuation_reached_horizon": reached,
                "abstention_reason": abstention,
                "any_nearby_same_colour_competitor": any(
                    s["other_same_colour_components_within_65px"]
                    for s in steps if s[
                        "other_same_colour_components_within_65px"] is not None),
                "terminal_to_nearest_same_colour_board_center_px_1080":
                    round(board_distance, 3) if board_distance is not None else None,
                "steps": steps,
                "persistent_stone_identity_verified": False,
                "simulation_ready": False,
            })
    finally:
        cap.release()
    result = {
        "status": "causal_local_cap_continuation_development_not_identity_truth",
        "source_video_sha256": source_hash,
        "input_sha256": {"replay_gaps": digest(GAPS),
                         "gap_inventory": digest(INVENTORY)},
        "runner_sha256": digest(Path(__file__)),
        "selector_code_sha256": digest(ROOT /
                                       "prototype/causal_cap_continuation.py"),
        "component_code_sha256": digest(ROOT /
                                        "prototype/local_colour_cap_probe.py"),
        "method": {
            "prediction": "constant pixel velocity from two past positions only",
            "search_radius_px": 90,
            "maximum_prediction_error_px": 65,
            "maximum_step_px": 110,
            "maximum_step_growth_vs_previous": 1.8,
            "step_growth_allowance_px": 12,
            "competition_margin_px": 15,
            "competition_distance_ratio": 1.5,
            "maximum_component_area_px2": 700,
            "future_board_used_for_selection": False,
            "future_board_used_for_horizon_and_diagnostic_only": True,
            "sampling_interval_s": 0.5,
        },
        "eligible_gap_count": len(rows),
        "reached_horizon_count": sum(r[
            "board_blind_continuation_reached_horizon"] for r in rows),
        "rows": rows,
        "limitations": [
            "This is a post-inspection development rule; thresholds were chosen after studying E001, E011 and E019.",
            "A unique image-cap match can switch physical stones during overlap, collision, occlusion or a camera cut.",
            "The first same-colour partial-board time defines the evaluation horizon, but no board position is used to select a cap.",
            "Centroid-to-board distance is a related-pixel diagnostic, not independent identity or metric error.",
            "Unobserved intervals remain between 2 Hz samples; no complete trajectories, event F1 or simulation-ready states follow.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"eligible": len(rows),
                      "reached_horizon": result["reached_horizon_count"],
                      "abstentions": {r["episode_id"]: r["abstention_reason"]
                                      for r in rows if r["abstention_reason"]}}))


if __name__ == "__main__":
    main()
