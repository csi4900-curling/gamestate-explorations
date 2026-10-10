"""Apply the same frozen 1 Hz stone-motion probe to every China counterless event."""

from hashlib import sha256
import json
from math import ceil, floor
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.stone_motion_fallback import verify_stone_motion_in_interval

VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
REVIEW = ROOT / "validation/official-shot-sequence/pwg2022-full-match-event-review-segments-v3-preorigin-travel-development.json"
HANDOFF = ROOT / "validation/official-shot-sequence/pwg2022-event-evidence-handoff-v3-development.json"
OUTPUT = ROOT / "validation/official-shot-sequence/china-all-counterless-motion-probe-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first all-counterless motion probe")
    review = json.loads(REVIEW.read_text())
    handoff = json.loads(HANDOFF.read_text())
    game = next(g for g in review["games"] if g["official_game_code"] == "PREL000102")
    evidence = next(g for g in handoff["games"] if g["recording_code"] == "PREL000102")
    if game["source_sha256"] != evidence["source_sha256"] or game["source_sha256"] != digest(VIDEO):
        raise ValueError("China source-video provenance mismatch")
    cues = {r["event_id"]: r for r in evidence["rows"]}
    events = [r for r in game["segments"] if r["counter_id"] is None]
    if len(events) != 9:
        raise ValueError("Counterless event inventory changed")
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {VIDEO}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for event in events:
            start = max(0, floor(event["delivery_window_s"][0]) - 5)
            end = ceil(event["delivery_window_s"][1]) + 15
            colour_tracks = {}
            for colour in ("red", "yellow"):
                result = verify_stone_motion_in_interval(cap, fps, colour=colour,
                                                          start_s=start, end_s=end)
                colour_tracks[colour] = [{"first_seen_s": track["points"][0]["time_s"],
                                          "last_seen_s": track["points"][-1]["time_s"],
                                          "span_px": round(track["span_px"], 2),
                                          "point_count": len(track["points"]),
                                          "points": track["points"]}
                                         for track in result["tracks"]]
            cue = cues[event["event_id"]]
            rows.append({"event_id": event["event_id"],
                         "delivery_window_s": event["delivery_window_s"],
                         "search_interval_s": [start, end],
                         "unique_release_cue_s": cue["release_cue"]["time_s"],
                         "release_cue_colour": cue["release_cue"]["colour"],
                         "receiving_view_colour": cue["receiving_view"]["colour"],
                         "colour_tracks": colour_tracks})
    finally:
        cap.release()
    result = {"status": "source_only_all_counterless_motion_probe_not_independent_labels",
              "source_video_sha256": digest(VIDEO),
              "review_sha256": digest(REVIEW), "handoff_sha256": digest(HANDOFF),
              "motion_detector_sha256": digest(ROOT / "prototype/stone_motion_fallback.py"),
              "runner_sha256": digest(Path(__file__)),
              "selection_rule": "All nine China counterless events; original delivery window -5 to +15 seconds, both colours, 1 Hz, frozen cap-track rule.",
              "event_count": len(rows), "rows": rows,
              "limitations": ["This selected-match diagnostic is not an independent event-F1 benchmark.",
                              "A moving cap may belong to an adjacent throw, equipment, or another sheet.",
                              "No track is not proof of no throw; camera cuts and low sampling can hide travel."]}
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    for row in rows:
        print(row["event_id"],
              {c: [(t["first_seen_s"], t["last_seen_s"], t["span_px"])
                   for t in row["colour_tracks"][c]] for c in ("red", "yellow")})


if __name__ == "__main__":
    main()
