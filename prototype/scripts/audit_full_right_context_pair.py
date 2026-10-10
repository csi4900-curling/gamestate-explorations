"""Apply frozen ring/underpoint review cues to every full-source right proposal."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from right_track_ice_context import three_sample_context
from right_track_underpoint_context import three_sample_underpoint


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def selected_points(proposal):
    points = proposal["observed_prefix_points"]
    if len(points) < 2:
        raise ValueError("Proposal has fewer than two observed points")
    passage_time = proposal["passage"]["time_s"]
    return [points[0], min(points, key=lambda row: abs(row["time_s"] - passage_time)),
            points[-1]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "video", "tail", "episodes", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    plan, tail, episodes = (json.loads(path.read_text()) for path in
                            (args.plan, args.tail, args.episodes))
    expected = {
        "source_sha256": digest(args.video),
        "right_tail_sha256": digest(args.tail),
        "episodes_sha256": digest(args.episodes),
        "ring_feature_code_sha256": digest(ROOT / "prototype/right_track_ice_context.py"),
        "underpoint_feature_code_sha256": digest(
            ROOT / "prototype/right_track_underpoint_context.py"),
    }
    if any(plan[key] != value for key, value in expected.items()):
        raise ValueError("Frozen input or feature code changed")
    if (tail["source_sha256"] != expected["source_sha256"] or
            episodes["source_sha256"] != expected["source_sha256"] or
            episodes["right_tail_sha256"] != expected["right_tail_sha256"]):
        raise ValueError("Input source lineage differs")
    proposal_by_id = {"R01:" + row["raw_track_id"]: row for row in
                      tail["directional_review_proposals"]}
    if len(proposal_by_id) != len(tail["directional_review_proposals"]):
        raise ValueError("Duplicate right proposal")
    episode_by_right = {}
    for episode in episodes["episodes"]:
        for right_id in episode["right_proposal_ids"]:
            if right_id in episode_by_right:
                raise ValueError("Right proposal appears in multiple episodes")
            episode_by_right[right_id] = episode
    if set(episode_by_right) != set(proposal_by_id):
        raise ValueError("Episode inventory does not preserve every right proposal")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for right_id, proposal in sorted(proposal_by_id.items()):
            points = selected_points(proposal)
            distinct_times = len({point["time_s"] for point in points})
            episode = episode_by_right[right_id]
            result = {
                "right_proposal_id": right_id,
                "episode_id": episode["episode_id"],
                "episode_kind": episode["episode_kind"],
                "member_left_candidate_ids": episode["member_left_candidate_ids"],
                "sample_source_times_s": [point["time_s"] for point in points],
                "distinct_sample_count": distinct_times,
                "physical_stone_identity_verified": False,
            }
            if distinct_times < 3:
                result["review_tier"] = "insufficient_distinct_samples"
                rows.append(result)
                continue
            frames = []
            for point in points:
                frame_index = round((point["time_s"] -
                                     tail["source_time_offset_s"]) * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise RuntimeError(f"Cannot decode 640x360 frame {frame_index}")
                frames.append(frame)
            ring = three_sample_context(frames, points)
            under = three_sample_underpoint(frames, points)
            ring_fraction = ring["median_nonice_ring_fraction"]
            under_fraction = under["median_underpoint_nonice_fraction"]
            result.update({
                "sample_nonice_ring_fractions": ring["sample_nonice_ring_fractions"],
                "median_nonice_ring_fraction": ring_fraction,
                "sample_underpoint_nonice_fractions": under[
                    "sample_underpoint_nonice_fractions"],
                "median_underpoint_nonice_fraction": under_fraction,
                "underpoint_available_sample_count": under["available_sample_count"],
                "review_tier": (
                    "underpoint_unavailable" if under_fraction is None else
                    "cluttered_context_review" if max(ring_fraction,
                                                       under_fraction) > 0.25 else
                    "clear_context_review"),
            })
            rows.append(result)
    finally:
        cap.release()
    counts = Counter((row["episode_kind"], row["review_tier"]) for row in rows)
    output = {
        "status": "same_source_full_right_context_diagnostic_not_event_decision",
        "source_sha256": expected["source_sha256"],
        "input_sha256": {"plan": digest(args.plan), "right_tail": digest(args.tail),
                         "episodes": digest(args.episodes)},
        "ring_feature_code_sha256": expected["ring_feature_code_sha256"],
        "underpoint_feature_code_sha256": expected[
            "underpoint_feature_code_sha256"],
        "runner_sha256": digest(Path(__file__)),
        "review_threshold": 0.25,
        "proposal_count": len(rows),
        "counts_by_episode_kind_and_tier": {
            kind: {tier: count for (group, tier), count in sorted(counts.items())
                   if group == kind}
            for kind in sorted({row["episode_kind"] for row in rows})},
        "rows": rows,
        "limitations": [
            "The Czechia source contributed to feature development; this is not independent transfer.",
            "Context tiers rank source review only; they do not establish a stone or throw.",
            "Painted ice, athletes, equipment, occlusion and camera cuts can change either fraction.",
            "An episode may have more than one right proposal, so episode and proposal counts differ.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"right_proposals": len(rows),
                      "counts": output["counts_by_episode_kind_and_tier"]}))


if __name__ == "__main__":
    main()
