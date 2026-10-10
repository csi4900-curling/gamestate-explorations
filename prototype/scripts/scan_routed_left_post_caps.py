"""Sample left-view colour caps after conditionally routed split-screen events."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from right_view_partial_board import stable_cap_candidates
from split_left_cap_proposals import LEFT_ROI_XYXY, left_colour_cap_proposals

OFFSETS_S = (25, 30, 35)
NEXT_CANDIDATE_GUARD_S = 1


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "sequence", "routes", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    sequence = json.loads(args.sequence.read_text())
    routes = json.loads(args.routes.read_text())
    source_hash = digest(args.video)
    if (sequence["source_sha256"] != source_hash or
            routes["source_sha256"] != source_hash or
            routes["sequence_sha256"] != digest(args.sequence)):
        raise ValueError("Video, sequence and routes have different provenance")
    route_rows = routes["rows"]
    if len(route_rows) != sequence["left_candidate_count"]:
        raise ValueError("Route coverage differs from left candidate count")
    all_times = sorted({row["observation_time_s"] for row in sequence["rows"]})
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened() or cap.get(cv2.CAP_PROP_FPS) != 30:
        raise RuntimeError("Cannot open expected 30-fps full source")
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / 30
    rows = []
    try:
        for route in route_rows:
            if route["conditional_receiving_view"] != "left":
                continue
            t = route["observation_time_s"]
            later = [value for value in all_times if value > t]
            next_t = later[0] if later else duration
            proposed_times = [round(t + offset, 3) for offset in OFFSETS_S]
            if proposed_times[-1] >= min(next_t - NEXT_CANDIDATE_GUARD_S,
                                          duration):
                rows.append({"candidate_id": route["candidate_id"],
                             "status": "abstain_next_candidate_or_source_too_soon",
                             "next_candidate_time_s": next_t,
                             "sample_times_s": [], "stable_cap_proposals": []})
                continue
            frames = []
            for sample_time in proposed_times:
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(sample_time * 30))
                ok, frame = cap.read()
                if not ok or frame.shape != (360, 640, 3):
                    raise RuntimeError(f"Cannot decode 640x360 source {sample_time}")
                frames.append({"time_s": sample_time,
                               "cap_candidates": left_colour_cap_proposals(frame)})
            stable = stable_cap_candidates(frames)
            rows.append({"candidate_id": route["candidate_id"],
                         "status": "partial_repeated_left_image_caps" if stable
                                   else "no_repeated_left_image_caps",
                         "next_candidate_time_s": next_t,
                         "sample_times_s": proposed_times,
                         "sample_frames": frames,
                         "stable_cap_proposals": stable,
                         "coordinate_frame": "full_source_left_camera_pixels_not_metric",
                         "camera_registration_verified": False,
                         "complete_board_verified": False,
                         "delivered_stone_identity_verified": False,
                         "physical_settle_verified": False,
                         "simulation_ready": False})
    finally:
        cap.release()
    output = {
        "status": "postreview_left_receiving_view_partial_cap_scan_not_board_truth",
        "source_sha256": source_hash,
        "sequence_sha256": digest(args.sequence),
        "routes_sha256": digest(args.routes),
        "proposal_code_sha256": digest(ROOT / "prototype/split_left_cap_proposals.py"),
        "stability_code_sha256": digest(ROOT / "prototype/right_view_partial_board.py"),
        "runner_sha256": digest(Path(__file__)),
        "left_roi_xyxy_360p": LEFT_ROI_XYXY,
        "offsets_after_candidate_s": OFFSETS_S,
        "next_candidate_guard_s": NEXT_CANDIDATE_GUARD_S,
        "conditional_left_route_count": sum(
            row["conditional_receiving_view"] == "left" for row in route_rows),
        "status_counts": dict(Counter(row["status"] for row in rows)),
        "rows": rows,
        "limitations": [
            "Routing and sample offsets were chosen after S38 source review; both matches are exposed development data.",
            "Colour blobs can be stones, people, equipment or graphics; repeated positions are image evidence only.",
            "No independent camera registration, physical settle, complete board or delivered-stone identity is verified.",
            "An unobserved throw before the next candidate can contaminate a sampled tail.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"source": sequence["source_id"],
                      "left_routes": output["conditional_left_route_count"],
                      "statuses": output["status_counts"]}))


if __name__ == "__main__":
    main()
