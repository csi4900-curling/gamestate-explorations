"""Replay reviewed Czech settle gaps with a local cap-fragment merge."""

from hashlib import sha256
import json
from math import dist
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cap_fragment_merge import merge_cap_fragments
from causal_cap_continuation import choose_next_cap
from local_colour_cap_probe import local_cap_components

BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
VIDEO = BASE / "source-1080p-full-format270.mp4"
LOWRES_VIDEO = BASE / "source-360p.mp4"
GAPS = BASE / "full-reviewed-stone-replay-gaps-development.json"
INVENTORY = BASE / "full-reviewed-settle-gap-cap-inventory-development.json"
BASELINE = BASE / "full-reviewed-stone-cap-continuations-development.json"
OUT = BASE / "full-reviewed-stone-fragment-merge-continuations-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def search_roi(prediction, radius=90):
    x,y = prediction
    return (max(0,int(x-radius)), max(0,int(y-radius)),
            min(1920,int(x+radius+1)), min(1080,int(y+radius+1)))


def main():
    if OUT.exists():
        raise ValueError("Fragment continuation output already exists")
    gaps, inventory, baseline = (json.loads(path.read_text()) for path in
                                 (GAPS, INVENTORY, BASELINE))
    source_hash = digest(VIDEO)
    if not (source_hash == inventory["source_video_sha256"] ==
            baseline["source_video_sha256"] and
            digest(LOWRES_VIDEO) == gaps["source_video_sha256"]):
        raise ValueError("Source hash mismatch")
    if (baseline["input_sha256"]["replay_gaps"] != digest(GAPS) or
            baseline["input_sha256"]["gap_inventory"] != digest(INVENTORY)):
        raise ValueError("Baseline input lineage differs")
    gap_by_episode = {row["episode_id"]: row for row in gaps["rows"]}
    baseline_by_episode = {row["episode_id"]: row for row in baseline["rows"]}
    if (len(gap_by_episode) != len(gaps["rows"]) or
            len(baseline_by_episode) != len(baseline["rows"]) or
            set(baseline_by_episode) != {row["episode_id"] for row in
                                        inventory["rows"]}):
        raise ValueError("Gap or baseline episode IDs differ")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened() or abs(cap.get(cv2.CAP_PROP_FPS)-30) > 0.01:
        raise ValueError("Source unreadable or frame rate differs")
    rows = []
    try:
        for case in inventory["rows"]:
            id = case["episode_id"]
            gap = gap_by_episode[id]
            path = gap["observed_left_motion_path"]
            if len(path) < 2:
                raise ValueError(f"Cannot seed continuation for {id}")
            previous, current = path[-2:]
            previous_center, current_center = (previous["pixel_center_1080"],
                                               current["pixel_center_1080"])
            previous_time, current_time = (previous["source_time_s"],
                                           current["source_time_s"])
            steps = []
            abstention = None
            for sample in case["samples"][1:]:
                time_s = sample["source_time_s"]
                dt_ratio = (time_s-current_time)/(current_time-previous_time)
                prediction = [current_center[i]+(current_center[i]-previous_center[i])*
                              dt_ratio for i in (0,1)]
                roi = search_roi(prediction)
                cap.set(cv2.CAP_PROP_POS_FRAMES, sample["decoded_frame_index"])
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (1080,1920):
                    raise ValueError(f"Source frame unreadable: {id} {time_s}")
                components = [item for item in local_cap_components(
                    frame,roi,case["colour_claim"]) if item["area_px2"] <= 700]
                merged = merge_cap_fragments(components)
                decision = choose_next_cap(current_center,previous_center,
                                           dt_ratio,merged)
                selected = decision["selected"]
                steps.append({"source_time_s":time_s,
                              "decoded_frame_index":sample["decoded_frame_index"],
                              "original_components":components,
                              "fragment_merged_components":merged,
                              "fragment_merge_count":sum(len(item[
                                  "merged_source_component_indices"])>1 for item in merged),
                              "decision":decision})
                if selected is None:
                    abstention = decision["status"]
                    break
                previous_center,current_center = current_center,selected[
                    "centroid_px_1080"]
                previous_time,current_time = current_time,time_s
            horizon = case["first_same_colour_board_time_s"]
            reached = bool(steps) and abstention is None and steps[-1][
                "source_time_s"] == horizon
            board_distance = (min(dist(current_center,center) for center in
                                  case["first_same_colour_board_centers_px_1080"])
                              if reached else None)
            old = baseline_by_episode[id]
            rows.append({
                "episode_id":id,
                "left_motion_candidate_id":case["left_motion_candidate_id"],
                "colour_claim":case["colour_claim"],
                "first_same_colour_board_time_s":horizon,
                "baseline_reached_horizon":old["board_blind_continuation_reached_horizon"],
                "baseline_abstention_reason":old["abstention_reason"],
                "fragment_aware_reached_horizon":reached,
                "fragment_aware_abstention_reason":abstention,
                "last_selected_source_time_s":current_time,
                "total_fragment_merges":sum(step["fragment_merge_count"] for step
                                            in steps),
                "terminal_to_nearest_same_colour_board_center_px_1080":
                    round(board_distance,3) if board_distance is not None else None,
                "steps":steps,
                "persistent_stone_identity_verified":False,
                "simulation_ready":False,
            })
    finally:
        cap.release()
    OUT.write_text(json.dumps({
        "status":"development_fragment_aware_cap_continuation_not_identity_truth",
        "source_video_sha256":source_hash,
        "low_resolution_source_video_sha256":gaps["source_video_sha256"],
        "input_sha256":{"replay_gaps":digest(GAPS),"gap_inventory":digest(INVENTORY),
                        "frozen_baseline":digest(BASELINE)},
        "code_sha256":{"runner":digest(Path(__file__)),
                       "fragment_merge":digest(ROOT/"prototype/cap_fragment_merge.py"),
                       "selector":digest(ROOT/"prototype/causal_cap_continuation.py"),
                       "components":digest(ROOT/"prototype/local_colour_cap_probe.py")},
        "eligible_gap_count":len(rows),
        "baseline_reached_horizon_count":sum(row["baseline_reached_horizon"] for row in rows),
        "fragment_aware_reached_horizon_count":sum(row["fragment_aware_reached_horizon"]
                                                   for row in rows),
        "rows":rows,
        "limitations":[
            "The fragment geometry was chosen after observing exposed E011 source pixels; this is not held-out tracking validation.",
            "Merging nearby colour components can hide two touching stones; geometric continuity is not physical identity.",
            "The future board is used only for the evaluation horizon and terminal-distance diagnostic, not for choosing a cap.",
            "Half-second sampling may miss brief occlusions or identity swaps; no complete trajectory or simulation-ready state is claimed.",
        ],
    },indent=2)+"\n")
    print(json.dumps({"baseline_reached":sum(row["baseline_reached_horizon"] for row in rows),
                      "fragment_aware_reached":sum(row["fragment_aware_reached_horizon"]
                                                   for row in rows),
                      "changed":[row["episode_id"] for row in rows if row[
                          "baseline_reached_horizon"]!=row["fragment_aware_reached_horizon"]]}))


if __name__=="__main__":
    main()
