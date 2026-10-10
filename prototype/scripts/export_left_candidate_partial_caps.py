"""Sample right-view image caps after every routed left proposal, including abstentions."""

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
from export_right_only_partial_caps import anchors_agree, observe_anchor


TAIL_OFFSETS_S = [15, 20, 25]
NEXT_CANDIDATE_GUARD_S = 1


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def guard_tail(row, next_time, run_end, duration):
    observed = row.get("observed_motion_interval_s")
    if observed is None:
        return "abstain_no_motion_time_bracket"
    if not (len(observed) == 2 and observed[0] <= row["source_time_s"] <= observed[1]):
        raise ValueError("Left candidate time outside observed motion bracket")
    tail_end = observed[1] + TAIL_OFFSETS_S[-1]
    if tail_end >= min(next_time - NEXT_CANDIDATE_GUARD_S, run_end, duration):
        return "abstain_next_candidate_or_route_boundary"
    return None


def export_observations(cap, fps, duration, union, timeline):
    if union["source_sha256"] != timeline["source_sha256"]:
        raise ValueError("Candidate and timeline sources differ")
    runs = {row["id"]: row for row in timeline["supported_runs"]}
    candidates = union["candidates"]
    if any(a["source_time_s"] > b["source_time_s"] for a, b in
           zip(candidates, candidates[1:])):
        raise ValueError("Candidate ledger is out of source order")
    rows = []
    for index, candidate in enumerate(candidates):
        if candidate["origin"] != "left_routed_proposal":
            continue
        run = runs[candidate["source_run_id"]]
        if run["layout"] != "split_2024":
            continue
        t = candidate["source_time_s"]
        if not run["interval_s"][0] <= t < run["interval_s"][1]:
            raise ValueError("Left candidate outside its routed interval")
        next_time = (candidates[index + 1]["source_time_s"]
                     if index + 1 < len(candidates) else duration)
        status = guard_tail(candidate, next_time, run["interval_s"][1], duration)
        observed = candidate.get("observed_motion_interval_s")
        base = {"candidate_id": candidate["candidate_id"],
                "source_time_s": t,
                "observed_motion_interval_s": observed,
                "next_candidate_time_s": next_time,
                "routed_run_end_s": run["interval_s"][1],
                "coordinate_frame": "normalized_640x360_source_right_camera_pixels_not_metric",
                "complete_board_verified": False,
                "physical_settle_verified": False,
                "persistent_stone_identity_verified": False,
                "simulation_ready": False}
        if status is not None:
            rows.append({**base, "observation_status": status,
                         "anchor_stability_agreement": None,
                         "sample_frames": [], "stable_cap_proposals": []})
            continue
        anchors = sorted({round(x, 3) for x in (observed[0], t, observed[1])})
        samples = [observe_anchor(cap, fps, duration, anchor)
                   for anchor in anchors]
        central = next(item for item in samples if item["anchor_time_s"] == t)
        agreement = anchors_agree(samples, central)
        status = (central["observation_status"] if agreement else
                  "abstain_motion_time_sensitive")
        rows.append({**base,
                     "observation_status": status,
                     "anchor_stability_agreement": agreement,
                     "anchor_observations": samples,
                     "sample_frames": central["sample_frames"],
                     "stable_cap_proposals": (central["stable_cap_proposals"]
                                              if agreement else [])})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--union", type=Path, required=True)
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    union = json.loads(args.union.read_text())
    timeline = json.loads(args.timeline.read_text())
    video_hash = digest(args.video)
    if video_hash != union["source_sha256"]:
        parser.error("Source video and candidates differ")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
    try:
        rows = export_observations(cap, fps, duration, union, timeline)
    finally:
        cap.release()
    result = {
        "status": "post_left_candidate_partial_right_image_caps_not_game_state",
        "source_sha256": video_hash,
        "input_sha256": {"candidate_review_union": digest(args.union),
                         "timeline": digest(args.timeline)},
        "runner_sha256": digest(Path(__file__)),
        "right_sampler_code_sha256": digest(
            ROOT / "prototype/scripts/export_right_only_partial_caps.py"),
        "proposal_code_sha256": digest(
            ROOT / "prototype/scripts/probe_static_left_right_cap_motion.py"),
        "frame_normalization_code_sha256": digest(
            ROOT / "prototype/scripts/audit_split_panel_freeze.py"),
        "stable_cap_code_sha256": digest(ROOT / "prototype/right_view_partial_board.py"),
        "cap_set_comparison_code_sha256": digest(ROOT / "prototype/right_view_cap_sequence.py"),
        "sample_offsets_after_candidate_s": TAIL_OFFSETS_S,
        "next_candidate_guard_s": NEXT_CANDIDATE_GUARD_S,
        "split_run_ids": [run["id"] for run in timeline["supported_runs"]
                          if run["layout"] == "split_2024"],
        "left_candidate_count": len(rows),
        "observation_status_counts": dict(Counter(row["observation_status"]
                                                  for row in rows)),
        "rows": rows,
        "limitations": [
            "All routed left proposals are sampled, including nonstones and withheld rows.",
            "The fixed right-house ROI can miss caps under camera changes or occlusion.",
            "Motion brackets are detection evidence, not physical throw boundaries.",
            "Candidate gaps do not rule out unobserved deliveries between samples.",
            "Stable image caps are not complete boards or persistent stone identities.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"left_candidates": len(rows),
                      "statuses": result["observation_status_counts"]}))


if __name__ == "__main__":
    main()
