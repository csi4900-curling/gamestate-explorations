"""Scan bounded official-shot gaps around visual-only candidates for cap motion."""

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys

import cv2


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from scene_cuts import scene_cut_evidence
from stone_motion_fallback import moving_cap_tracks, stone_cap_candidates

REFERENCE = ROOT / "validation/official-shot-sequence/pwg2022-official-shot-ledger.json"
GAPS = ROOT / "validation/official-shot-sequence/pwg2022-official-gap-review.json"
OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-bounded-gap-motion-probe.json"
NEGATIVE_WINDOWS_S = ((10, 40), (120, 150), (8120, 8150), (8220, 8250))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scan(cap, fps, start_s, end_s, colour):
    sample_period_s = 0.2
    observations = []
    relaxed_observations = []
    cuts = []
    previous = None
    first_tick = max(0, math.floor(start_s / sample_period_s) - 25)
    last_tick = math.ceil(end_s / sample_period_s) + 50
    for tick in range(first_tick, last_tick + 1):
        second = round(tick * sample_period_s, 3)
        cap.set(cv2.CAP_PROP_POS_FRAMES, round(second * fps))
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"Frame decode failed at {second}s")
        if previous is not None and scene_cut_evidence(previous, frame)["hard_cut"]:
            cuts.append(float(second))
        observations.append((second, stone_cap_candidates(frame, colour)))
        relaxed_observations.append((second, stone_cap_candidates(
            frame, colour, allow_bright_body=True, allow_large_caps=True)))
        previous = frame
    fine_tracks = moving_cap_tracks(observations, max_gap_s=0.5, cut_times_s=cuts)
    relaxed_tracks = moving_cap_tracks(relaxed_observations, max_gap_s=0.5, cut_times_s=cuts)
    coarse_observations = [(time_s, candidates) for time_s, candidates in observations
                           if abs(time_s - round(time_s)) < 0.001]
    coarse_tracks = moving_cap_tracks(coarse_observations, cut_times_s=cuts)

    def summarize(tracks):
        return [{
            "time_interval_s": [track["points"][0]["time_s"], track["points"][-1]["time_s"]],
            "observation_count": len(track["points"]),
            "span_px": round(track["span_px"], 2),
            "first_pixel_640x360": track["points"][0]["pixel"],
            "last_pixel_640x360": track["points"][-1]["pixel"],
        } for track in tracks]

    return {
        "scan_interval_s": [observations[0][0], observations[-1][0]],
        "sample_period_s": sample_period_s,
        "hard_cut_times_s": cuts,
        "fine_track_count": len(fine_tracks),
        "fine_tracks": summarize(fine_tracks),
        "coarse_track_count": len(coarse_tracks),
        "coarse_tracks": summarize(coarse_tracks),
        "relaxed_fine_track_count": len(relaxed_tracks),
        "relaxed_fine_tracks": summarize(relaxed_tracks),
    }


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first visual gap probe")
    reference = json.loads(REFERENCE.read_text())
    gaps = json.loads(GAPS.read_text())
    if gaps["official_reference_sha256"] != digest(REFERENCE):
        raise ValueError("Gap packet does not match official reference")
    sources = {game["official_game_code"]: game for game in reference["games"]}
    results = []
    for game in gaps["games"]:
        source = sources[game["official_game_code"]]
        video = ROOT / source["source_video_path"]
        if digest(video) != source["source_video_sha256"]:
            raise ValueError("Video does not match official reference")
        cap = cv2.VideoCapture(str(video))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open {video}")
        fps = cap.get(cv2.CAP_PROP_FPS)
        for run in game["gap_runs"]:
            visual = [row for row in run["candidate_windows_intersecting_span"]
                      if row["counter_id"] is None]
            if not run["bounded_within_end"] or len(run["official_shots"]) != 1 or len(visual) != 1:
                continue
            candidate = visual[0]
            colour = run["official_shots"][0]["colour"]
            motion = scan(cap, fps, *candidate["release_window_s"], colour)
            results.append({
                "official_game_code": game["official_game_code"],
                "official_shot_id": run["official_shots"][0]["official_shot_id"],
                "expected_colour": colour,
                "candidate_id": candidate["candidate_id"],
                "candidate_colour": candidate["colour"],
                "candidate_release_window_s": candidate["release_window_s"],
                "counter_bounded_review_span_s": run["review_search_span_s"],
                "candidate_colour_triage": run["visual_candidate_triage"],
                **motion,
            })
        cap.release()
    negative_source = sources["PREL000102"]
    negative_video = ROOT / negative_source["source_video_path"]
    cap = cv2.VideoCapture(str(negative_video))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {negative_video}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    negative_controls = []
    for start, end in NEGATIVE_WINDOWS_S:
        for colour in ("red", "yellow"):
            negative_controls.append({"source_window_s": [start, end], "colour": colour,
                                      **scan(cap, fps, start, end, colour)})
    cap.release()
    output = {
        "status": "source_video_cap_motion_diagnostic_not_throw_confirmation",
        "official_reference_sha256": digest(REFERENCE),
        "gap_review_sha256": digest(GAPS),
        "source_detector_sha256": digest(ROOT / "prototype/stone_motion_fallback.py"),
        "scene_cut_code_sha256": digest(ROOT / "prototype/scene_cuts.py"),
        "runner_sha256": digest(Path(__file__)),
        "probed_run_count": len(results),
        "fine_track_count_distribution": dict(Counter(str(row["fine_track_count"]) for row in results)),
        "coarse_track_count_distribution": dict(Counter(str(row["coarse_track_count"]) for row in results)),
        "relaxed_fine_track_count_distribution": dict(Counter(
            str(row["relaxed_fine_track_count"]) for row in results)),
        "runs_with_a_strict_track_on_either_scale": sum(
            bool(row["fine_track_count"] or row["coarse_track_count"]) for row in results),
        "runs_with_a_relaxed_fine_track": sum(bool(row["relaxed_fine_track_count"])
                                                for row in results),
        "results": results,
        "negative_control_source_video_sha256": negative_source["source_video_sha256"],
        "negative_control_provenance": "Previously exposed source-only nonthrow opening and closing intervals; development controls, not independent held-out labels.",
        "negative_controls": negative_controls,
        "limitations": [
            "A coloured cap track can be an already moving stone, a player, or camera motion; this is not independent event validation.",
            "A missing track is not proof of a missed delivery; small, occluded or differently coloured stones can evade this detector.",
            "The scan is centred on development candidate windows and therefore cannot establish full-video recall.",
            "The source videos and official results are independent of the candidate detector, but candidate-chosen scan windows are not.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(output["probed_run_count"], output["fine_track_count_distribution"],
          output["coarse_track_count_distribution"],
          output["relaxed_fine_track_count_distribution"])


if __name__ == "__main__":
    main()
