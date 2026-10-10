"""Score live-overlay and local-ice evidence for dense Beijing gap tracks."""

import argparse
import json
from pathlib import Path
import statistics
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from learned_gap_confirmation import (
    compact_overlay_patch,
    compact_overlay_visible,
    confirm_dense_gap_candidates,
    local_ice_fraction,
    longest_smooth_motion_run,
    overlay_distance,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--large-cap-fallback", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve the first result")
    source = json.loads(args.candidates.read_text())
    digest = file_sha256(args.video)
    if digest != source["source_sha256"]:
        parser.error("Video fingerprint differs from candidate artifact")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if digest == reserved["source_sha256"]:
        parser.error("Reserved source cannot be used for development")
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        capture.release()
        parser.error("Unreadable video")
    cache = {}

    def frame_at(time_s):
        if time_s not in cache:
            capture.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Frame decode failed at {time_s} s")
            cache[time_s] = frame
        return cache[time_s]

    templates = {}
    template_times = {}
    for gap in source["scanned_gaps"]:
        start, end = gap["interval_s"]
        selected = next(
            (float(t) for t in range(int(start), int(end)) if compact_overlay_visible(frame_at(float(t)))),
            None,
        )
        template_times[gap["id"]] = selected
        templates[gap["id"]] = compact_overlay_patch(frame_at(selected)) if selected is not None else None
    context = []
    for candidate in source["motion_candidates"]:
        points = candidate["visual_track_points"]
        count = min(5, len(points))
        sampled = [points[round(i * (len(points) - 1) / (count - 1))] for i in range(count)]
        template = templates[candidate["gap_id"]]
        overlay = []
        local_ice = []
        live_overlay = []
        for point in sampled:
            frame = frame_at(point["time_s"])
            overlay.append(overlay_distance(frame, template) if template is not None else 1.0)
            local_ice.append(local_ice_fraction(frame, point["bbox"]))
            live_overlay.append(compact_overlay_visible(frame))
        first = np.asarray(points[0]["pixel"], float)
        last = np.asarray(points[-1]["pixel"], float)
        xy = np.asarray([point["pixel"] for point in points], float)
        steps = np.linalg.norm(np.diff(xy, axis=0), axis=1)
        context.append(
            {
                "id": candidate["id"],
                "median_overlay_distance": round(statistics.median(overlay), 5),
                "median_local_ice_fraction": round(statistics.median(local_ice), 5),
                "net_displacement_px": round(float(np.linalg.norm(last - first)), 3),
                "moving_steps_gt4px": int(np.sum(steps > 4)),
                "live_overlay_sample_fraction": round(sum(live_overlay) / count, 3),
                "sampled_times_s": [point["time_s"] for point in sampled],
                **longest_smooth_motion_run(points),
            }
        )
    capture.release()
    decisions = confirm_dense_gap_candidates(
        source["motion_candidates"], context,
        min_smooth_run_s=2.0 if args.large_cap_fallback else 0,
        min_smooth_run_moving_steps=8 if args.large_cap_fallback else 0,
    )
    accepted = {row["id"] for row in decisions if row["status"] == "corroborated_gap_candidate"}
    result = {
        "status": "development_dense_gap_context_screen",
        "source_id": source["source_id"],
        "source_sha256": digest,
        "source_interval_s": source["source_interval_s"],
        "input_sha256": file_sha256(args.candidates),
        "model_sha256": file_sha256(ROOT / "prototype/learned_gap_confirmation.py"),
        "runner_sha256": file_sha256(__file__),
        "template_times_s": template_times,
        "template_policy": "First whole-second frame with the compact live overlay in each gap; no manual choice",
        "large_cap_fallback": args.large_cap_fallback,
        "context": context,
        "decisions": decisions,
        "corroborated_candidates": [
            item for item in source["motion_candidates"] if item["id"] in accepted
        ],
        "withheld_candidates": [
            item for item in source["motion_candidates"] if item["id"] not in accepted
        ],
        "limitations": [
            "Overlay and local-ice thresholds were chosen after inspecting Slovakia–USA G02.",
            "A score overlay is only a broadcast cue, not proof that an image shows live play.",
            "Episode grouping does not prove identity continuity across cuts or collisions.",
            "Candidates are not promoted to confirmed throw events.",
        ],
    }
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"corroborated": len(result["corroborated_candidates"]),
                      "withheld": len(result["withheld_candidates"])}))


if __name__ == "__main__":
    main()
