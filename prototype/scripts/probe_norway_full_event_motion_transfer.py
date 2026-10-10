"""Transfer the frozen 1 Hz coloured-cap motion rule to all Norway candidates."""

from collections import Counter
from hashlib import sha256
import json
from math import ceil, floor
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.stone_motion_fallback import verify_stone_motion_in_interval

LEDGER = ROOT / "validation/curlobserver-learned-probe/canada-norway-full-transfer/fused-linked.json"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
OUTPUT = ROOT / "validation/official-shot-sequence/norway-full-event-motion-transfer-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first full Norway motion transfer")
    ledger = json.loads(LEDGER.read_text())
    events = ledger["events"]
    if ledger["source_sha256"] != digest(VIDEO) or len(events) != 141:
        raise ValueError("Norway ledger or source video changed")
    if len({e["shot_id"] for e in events}) != len(events):
        raise ValueError("Duplicate Norway shot IDs")
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
                                          "first_pixel": track["points"][0]["pixel"],
                                          "last_pixel": track["points"][-1]["pixel"]}
                                         for track in result["tracks"]]
            rows.append({"shot_id": event["shot_id"], "counter_id": event["counter_id"],
                         "candidate_colour": event["colour"],
                         "evidence_sources": event["evidence_sources"],
                         "delivery_window_s": event["delivery_window_s"],
                         "search_interval_s": [start, end],
                         "colour_tracks": colour_tracks,
                         "any_supported_motion": any(colour_tracks.values())})
    finally:
        cap.release()
    grouped = {}
    for label, subset in (("counter_backed", [r for r in rows if r["counter_id"] is not None]),
                          ("counterless", [r for r in rows if r["counter_id"] is None])):
        grouped[label] = {"candidate_count": len(subset),
                          "with_supported_motion": sum(r["any_supported_motion"] for r in subset),
                          "track_colours": dict(Counter(colour for r in subset
                                                        for colour in ("red", "yellow")
                                                        if r["colour_tracks"][colour]))}
    result = {"status": "first_source_only_norway_full_candidate_motion_transfer_not_event_f1",
              "source_video_sha256": digest(VIDEO),
              "candidate_ledger_sha256": digest(LEDGER),
              "motion_detector_sha256": digest(ROOT / "prototype/stone_motion_fallback.py"),
              "runner_sha256": digest(Path(__file__)),
              "selection_rule": "Every one of 141 Norway candidate windows; window -5 to +15 seconds, both colours, 1 Hz, frozen cap-track rule.",
              "candidate_count": len(rows), "groups": grouped, "rows": rows,
              "limitations": ["Candidate status and broadcast-counter links are development proxies, not independent throw labels.",
                              "A moving cap can belong to equipment, another sheet, or an adjacent throw.",
                              "No track is not proof of no throw; camera cuts and 1 Hz sampling can hide motion."]}
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(grouped)


if __name__ == "__main__":
    main()
