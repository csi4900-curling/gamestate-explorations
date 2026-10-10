"""Rerun all frozen Norway windows with hard-cut-aware track linking."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from prototype.stone_motion_fallback import verify_stone_motion_in_interval


VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
BASELINE = ROOT / "validation/official-shot-sequence/norway-full-event-motion-transfer-first.json"
OUTPUT = ROOT / "validation/official-shot-sequence/norway-full-event-motion-cut-aware-v2.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def summarize_track(track):
    points = track["points"]
    return {"first_seen_s": points[0]["time_s"],
            "last_seen_s": points[-1]["time_s"],
            "span_px": round(track["span_px"], 2),
            "point_count": len(points),
            "first_pixel": points[0]["pixel"],
            "last_pixel": points[-1]["pixel"]}


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first cut-aware transfer")
    baseline = json.loads(BASELINE.read_text())
    if len(baseline["rows"]) != baseline["candidate_count"]:
        raise SystemExit("Baseline candidate count disagrees")
    video_hash = digest(VIDEO)
    if video_hash != baseline["source_video_sha256"]:
        raise SystemExit("Video changed since baseline transfer")
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {VIDEO}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for index, row in enumerate(baseline["rows"], 1):
            start, end = row["search_interval_s"]
            results = {colour: verify_stone_motion_in_interval(
                cap, fps, colour=colour, start_s=start, end_s=end,
                detect_hard_cuts=True) for colour in ("red", "yellow")}
            red_cuts = results["red"]["hard_cut_times_s"]
            yellow_cuts = results["yellow"]["hard_cut_times_s"]
            if red_cuts != yellow_cuts:
                raise RuntimeError(f"Inconsistent cut times for {row['shot_id']}")
            colour_tracks = {colour: [summarize_track(track) for track in results[colour]["tracks"]]
                             for colour in ("red", "yellow")}
            rows.append({key: row[key] for key in
                         ("shot_id", "counter_id", "candidate_colour", "evidence_sources",
                          "delivery_window_s", "search_interval_s")}
                        | {"hard_cut_times_s": red_cuts,
                           "colour_tracks": colour_tracks,
                           "any_supported_motion": any(colour_tracks.values())})
            if index % 20 == 0:
                print(f"processed {index}/{len(baseline['rows'])}", flush=True)
    finally:
        cap.release()
    groups = {}
    for label, subset in (("counter_backed", [r for r in rows if r["counter_id"] is not None]),
                          ("counterless", [r for r in rows if r["counter_id"] is None])):
        groups[label] = {"candidate_count": len(subset),
                         "with_supported_motion": sum(r["any_supported_motion"] for r in subset),
                         "with_detected_hard_cut": sum(bool(r["hard_cut_times_s"]) for r in subset),
                         "track_colours": dict(Counter(colour for r in subset
                                                       for colour in ("red", "yellow")
                                                       if r["colour_tracks"][colour]))}
    result = {
        "status": "first_source_only_norway_cut_aware_motion_transfer_not_event_f1",
        "source_video_sha256": video_hash,
        "baseline_motion_transfer_sha256": digest(BASELINE),
        "motion_detector_sha256": digest(ROOT / "prototype/stone_motion_fallback.py"),
        "scene_cut_detector_sha256": digest(ROOT / "prototype/scene_cuts.py"),
        "runner_sha256": digest(Path(__file__)),
        "selection_rule": "All frozen 141 Norway windows, both colours, 1 Hz; same cap rule with conservative hard-cut breaks.",
        "candidate_count": len(rows), "groups": groups, "rows": rows,
        "limitations": [
            "Only obvious hard cuts at 1 Hz are detected; subtle edits and edits between samples may be missed.",
            "A cap track within one camera shot is motion evidence, not independently verified throw identity.",
            "No track does not reject a candidate throw; camera coverage and sampling remain incomplete.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(groups)


if __name__ == "__main__":
    main()
