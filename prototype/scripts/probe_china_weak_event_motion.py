"""Run frozen coloured-cap motion tracks on four China visual-only windows."""

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
OUTPUT = ROOT / "validation/official-shot-sequence/china-weak-event-motion-probe-first.json"
IDS = ("VISUAL-S52", "VISUAL-S360", "VISUAL-S403", "VISUAL-S411")


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first weak-event motion probe")
    source = json.loads(REVIEW.read_text())
    game = next(g for g in source["games"] if g["official_game_code"] == "PREL000102")
    if game["source_sha256"] != digest(VIDEO):
        raise ValueError("Source video differs from frozen review")
    selected = {row["event_id"]: row for row in game["segments"] if row["event_id"] in IDS}
    if set(selected) != set(IDS) or any(selected[key]["counter_id"] is not None for key in IDS):
        raise ValueError("Weak candidate selection changed")
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {VIDEO}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for event_id in IDS:
            row = selected[event_id]
            start = max(0, floor(row["delivery_window_s"][0]) - 5)
            end = ceil(row["delivery_window_s"][1]) + 15
            colours = {}
            for colour in ("red", "yellow"):
                result = verify_stone_motion_in_interval(cap, fps, colour=colour,
                                                          start_s=start, end_s=end)
                colours[colour] = {
                    "track_count": len(result["tracks"]),
                    "tracks": [{"first_seen_s": track["points"][0]["time_s"],
                                "last_seen_s": track["points"][-1]["time_s"],
                                "span_px": round(track["span_px"], 2),
                                "point_count": len(track["points"]),
                                "points": track["points"]}
                               for track in result["tracks"]],
                }
            rows.append({"event_id": event_id, "delivery_window_s": row["delivery_window_s"],
                         "search_interval_s": [start, end], "colours": colours})
    finally:
        cap.release()
    output = {"status": "source_only_frozen_motion_probe_not_throw_validation",
              "source_video_sha256": digest(VIDEO),
              "review_sha256": digest(REVIEW),
              "motion_detector_sha256": digest(ROOT / "prototype/stone_motion_fallback.py"),
              "runner_sha256": digest(Path(__file__)),
              "selection_rule": "Four China visual-window-only counterless candidates; original delivery window -5 to +15 seconds, both colours, 1 Hz, frozen cap-track rule.",
              "event_count": len(rows), "rows": rows,
              "limitations": ["A coloured-cap track can be equipment, a neighbouring sheet, or a different throw.",
                              "Single-frame-per-second tracking can miss or merge moving stones across camera cuts.",
                              "A missing track is not proof that no throw occurred; no event tier is changed by this probe."]}
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    for row in rows:
        print(row["event_id"], {colour: [(t["first_seen_s"], t["last_seen_s"], t["span_px"])
                                         for t in row["colours"][colour]["tracks"]]
                                for colour in ("red", "yellow")})


if __name__ == "__main__":
    main()
