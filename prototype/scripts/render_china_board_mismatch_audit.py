"""Render a postscore visual audit of persistent China board mismatches.

This illustration is diagnostic only. It is not an input to the source-only
board detector or a source of independent labels.
"""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.scripts.scan_china_full_match_boards import read_frame
from prototype.video_board_observation_v2 import detect_overhead_house

BASE = ROOT / "validation/official-shot-sequence"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
SCAN = BASE / "china-full-match-event-gated-source-video-boards-first.json"
SCORE = BASE / "china-full-match-event-gated-video-board-first-score.json"
OUTPUT = BASE / "china-board-mismatch-audit.png"
PROVENANCE = BASE / "china-board-mismatch-audit.json"
SELECTION = ("B40", "B41", "B42", "B43", "B44", "B47")


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def unmatched_stones(stones, comparison):
    by_colour = {colour: [s for s in stones if s["colour"] == colour]
                 for colour in ("red", "yellow")}
    return [by_colour[row["colour"]][row["video_index"]]
            for row in comparison["unmatched_video"]]


def main():
    if OUTPUT.exists() or PROVENANCE.exists():
        raise SystemExit("Audit artifact exists; preserve first review")
    scan = json.loads(SCAN.read_text())
    score = json.loads(SCORE.read_text())
    if scan["source_video_sha256"] != digest(VIDEO) or score["source_only_scan_sha256"] != digest(SCAN):
        raise ValueError("Source-only scan, score, or video provenance mismatch")
    scans = {r["counter_id"]: r for r in scan["rows"]}
    scores = {r["counter_id"]: r for r in score["rows"]}
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {VIDEO}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    font = ImageFont.load_default()
    canvas = Image.new("RGB", (1280, 3 * 405), "#f2f3f5")
    rows = []
    try:
        for i, counter_id in enumerate(SELECTION):
            observation = scans[counter_id]
            scored = scores[counter_id]
            stones = unmatched_stones(observation["stable_partial_board"],
                                      scored["current_comparison"])
            if not stones:
                raise ValueError(f"{counter_id} no longer has unmatched video stones")
            time_s = min(stone["last_seen_s"] for stone in stones)
            if time_s < max(stone["first_seen_s"] for stone in stones):
                raise ValueError(f"{counter_id} has no shared visible sample time")
            frame = read_frame(cap, fps, time_s)
            if frame is None:
                raise RuntimeError(f"Frame unavailable at {time_s}")
            house = detect_overhead_house(frame)
            if house is None:
                raise RuntimeError(f"House unavailable at {counter_id}, {time_s}")
            panel = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(panel)
            cx, cy = house["center_px"]
            radius = house["outer_radius_px"]
            side = observation["local_inferred_delivery_side"]
            sign = 1 if side == "top" else -1
            marks = []
            for stone in stones:
                x = cx + sign * stone["canonical_lateral_house_radii"] * radius
                y = cy + sign * stone["longitudinal_house_radii"] * radius
                draw.ellipse((x - 15, y - 15, x + 15, y + 15), outline="#ff4c00", width=3)
                marks.append({"colour": stone["colour"],
                              "position_house_radii": [stone["canonical_lateral_house_radii"],
                                                       stone["longitudinal_house_radii"]],
                              "marked_pixel": [round(x, 1), round(y, 1)]})
            x0, y0 = (i % 2) * 640, (i // 2) * 405
            canvas.paste(panel, (x0, y0 + 45))
            header = ImageDraw.Draw(canvas)
            header.text((x0 + 14, y0 + 11),
                        f"{counter_id}  t={time_s:.1f}s  video/official: "
                        f"{scored['video_stone_count']}/{scored['official_symbol_count']}",
                        fill="#111827", font=font)
            rows.append({"counter_id": counter_id, "source_time_s": time_s,
                         "official_shot_id": scored["official_shot_id"],
                         "unmatched_video_marks": marks})
    finally:
        cap.release()
    canvas.save(OUTPUT)
    record = {"status": "postscore_visual_diagnostic_not_detector_input",
              "source_video_sha256": digest(VIDEO), "source_only_scan_sha256": digest(SCAN),
              "postscore_sha256": digest(SCORE), "runner_sha256": digest(Path(__file__)),
              "output_sha256": digest(OUTPUT), "rows": rows,
              "limitations": ["Orange circles are detections unmatched to PDF symbols, not independently labelled false positives.",
                              "The comparison cannot distinguish an out-of-play stone, wrong colour, or official-diagram omission without source review."]}
    PROVENANCE.write_text(json.dumps(record, indent=2) + "\n")
    print({"panels": len(rows), "output": str(OUTPUT), "sha256": record["output_sha256"]})


if __name__ == "__main__":
    main()
