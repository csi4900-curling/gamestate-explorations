"""Full-source 2024 right-entry proposal replay with exposed expanded ROI.

The output is a candidate audit, not accepted physical throws or an F1 score.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from expanded_right_colour import expanded_right_colour_proposals
from right_view_entry_triage import triage_tracks
from stone_motion_fallback import moving_cap_tracks


def digest(path):
    value = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def associate_baseline(baseline, expanded, *, max_time_gap_s=3):
    """One-to-one time/colour comparison, not a physical identity join."""
    pairs = []
    used = set()
    for old in baseline:
        choices = []
        for index, new in enumerate(expanded):
            if index in used or old["colour_claim"] != new["colour_claim"]:
                continue
            gap = abs(old["entry_crossing"]["time_s"] -
                      new["entry_crossing"]["time_s"])
            if gap <= max_time_gap_s:
                choices.append((gap, index))
        if choices:
            gap, index = min(choices)
            used.add(index)
            pairs.append({"baseline_id": old["raw_track_id"],
                          "expanded_id": expanded[index]["raw_track_id"],
                          "crossing_time_difference_s": round(gap, 3)})
    return {"time_colour_pairs": pairs,
            "unpaired_baseline_ids": [row["raw_track_id"] for row in baseline
                                      if row["raw_track_id"] not in {pair["baseline_id"] for pair in pairs}],
            "unpaired_expanded_ids": [row["raw_track_id"] for i, row in enumerate(expanded)
                                      if i not in used]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    baseline = json.loads(args.baseline.read_text())
    source_hash = digest(args.video)
    if source_hash != baseline["source_sha256"]:
        parser.error("Video and baseline sources differ")
    start, stop = baseline["source_interval_s"]
    if not isinstance(start, int) or not isinstance(stop, int):
        parser.error("Expected whole-second baseline interval")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    observations = {"red": [], "yellow": []}
    try:
        for time_s in range(start, stop + 1):
            cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Could not decode {time_s}s")
            found = expanded_right_colour_proposals(frame)
            for colour in observations:
                observations[colour].append((float(time_s), found[colour]))
    finally:
        cap.release()
    tracks = []
    for colour, samples in observations.items():
        for path in moving_cap_tracks(samples, max_gap_s=2, max_step_px=25):
            tracks.append({"colour": colour,
                           "first_observed_s": path["points"][0]["time_s"],
                           "last_observed_s": path["points"][-1]["time_s"],
                           "observation_count": len(path["points"]),
                           "span_px": path["span_px"],
                           "points": path["points"],
                           "physical_throw_verified": False})
    tracks.sort(key=lambda row: (row["first_observed_s"], row["colour"]))
    for index, row in enumerate(tracks, 1):
        row["track_id"] = f"E{index:03d}"
    entries = triage_tracks(tracks)
    comparison = associate_baseline(baseline["entry_review_proposals"], entries)
    output = {
        "status": "expanded_right_full_source_candidate_transfer_not_throw_score",
        "source_sha256": source_hash,
        "source_interval_s": [start, stop],
        "baseline_sha256": digest(args.baseline),
        "expanded_detector_code_sha256": digest(ROOT / "prototype/expanded_right_colour.py"),
        "tracker_code_sha256": digest(ROOT / "prototype/stone_motion_fallback.py"),
        "entry_tier_code_sha256": digest(ROOT / "prototype/right_view_entry_triage.py"),
        "runner_sha256": digest(Path(__file__)),
        "sample_period_s": 1,
        "raw_track_count": len(tracks),
        "expanded_entry_review_count": len(entries),
        "baseline_entry_review_count": len(baseline["entry_review_proposals"]),
        "time_colour_comparison": comparison,
        "raw_tracks": tracks,
        "entry_review_proposals": entries,
        "limitations": [
            "The expanded ROI and area ceiling were chosen after inspecting Scotland.",
            "The original early-entry triage is reused unchanged, but greedy raw tracks can change when proposal density changes.",
            "Time/colour pairs are not persistent stone identities or physical throw labels.",
            "Novel proposals require source-first review; proposal counts are not recall or precision.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"raw_tracks": len(tracks), "expanded_entries": len(entries),
                      "paired": len(comparison["time_colour_pairs"]),
                      "baseline_unpaired": len(comparison["unpaired_baseline_ids"]),
                      "expanded_unpaired": len(comparison["unpaired_expanded_ids"])}))


if __name__ == "__main__":
    main()
