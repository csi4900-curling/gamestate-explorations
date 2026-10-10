"""Render source-only review sheets for China events without counter anchors."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.scripts.scan_china_full_match_boards import read_frame
from prototype.source_colour_reconciliation import reconcile_event_colour

BASE = ROOT / "validation/official-shot-sequence"
REVIEW = BASE / "pwg2022-full-match-event-review-segments-v3-preorigin-travel-development.json"
HANDOFF = BASE / "pwg2022-event-evidence-handoff-v3-development.json"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
OUTDIR = BASE / "china-counterless-event-audit"
MANIFEST = OUTDIR / "manifest.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def sample_times(event, evidence):
    start, end = event["delivery_window_s"]
    cue = evidence["release_cue"]["time_s"]
    if cue is not None:
        return [round(max(start, cue - 4), 1), round(cue, 1), round(min(end + 2, cue + 4), 1)]
    return [round(start + 2, 1), round((start + end) / 2, 1), round(end - 2, 1)]


def main():
    if MANIFEST.exists():
        raise SystemExit("Counterless audit exists; preserve first source-frame review")
    review = json.loads(REVIEW.read_text())
    handoff = json.loads(HANDOFF.read_text())
    game = next(g for g in review["games"] if g["official_game_code"] == "PREL000102")
    evidence = next(g for g in handoff["games"] if g["recording_code"] == "PREL000102")
    if game["source_sha256"] != evidence["source_sha256"] or game["source_sha256"] != digest(VIDEO):
        raise ValueError("Source-video provenance mismatch")
    handoff_rows = {r["event_id"]: r for r in evidence["rows"]}
    candidates = [row for row in game["segments"] if row["counter_id"] is None]
    if len(candidates) != 9:
        raise ValueError("China counterless candidate inventory changed")
    OUTDIR.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {VIDEO}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    font = ImageFont.load_default()
    records = []
    try:
        for page_index in range(3):
            rows = candidates[page_index * 3:(page_index + 1) * 3]
            sheet = Image.new("RGB", (3 * 640, 3 * 390), "#f3f5f4")
            draw = ImageDraw.Draw(sheet)
            for row_index, event in enumerate(rows):
                hand = handoff_rows[event["event_id"]]
                colour = reconcile_event_colour(event["colour"], hand["release_cue"],
                                                hand["receiving_view"])
                times = sample_times(event, hand)
                for column, time_s in enumerate(times):
                    frame = read_frame(cap, fps, time_s)
                    if frame is None:
                        raise RuntimeError(f"Frame unavailable at {time_s}")
                    x, y = column * 640, row_index * 390
                    sheet.paste(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)), (x, y + 30))
                    draw.text((x + 9, y + 8),
                              f"{event['event_id']} · {time_s:.1f}s · {colour['colour'] or '?'}",
                              fill="#172b27", font=font)
                records.append({"event_id": event["event_id"],
                                "delivery_window_s": event["delivery_window_s"],
                                "source_shots": event["review_shot_ids"],
                                "review_colour": event["colour"],
                                "reconciled_colour": colour["colour"],
                                "colour_status": colour["status"],
                                "release_cue": hand["release_cue"],
                                "receiving_view_status": hand["receiving_view"]["status"],
                                "sample_times_s": times,
                                "sheet": f"sheet-{page_index+1:02}.png"})
            sheet.save(OUTDIR / f"sheet-{page_index+1:02}.png")
    finally:
        cap.release()
    result = {"status": "source_only_counterless_candidate_review_sheets_no_official_labels",
              "source_video_sha256": digest(VIDEO),
              "review_sha256": digest(REVIEW), "handoff_sha256": digest(HANDOFF),
              "colour_reconciliation_sha256": digest(ROOT / "prototype/source_colour_reconciliation.py"),
              "runner_sha256": digest(Path(__file__)),
              "counterless_candidate_count": len(records),
              "sheet_sha256": {f"sheet-{i:02}.png": digest(OUTDIR / f"sheet-{i:02}.png")
                               for i in range(1, 4)},
              "rows": records,
              "limitations": ["Three sparse frames per candidate are a review aid, not a complete physical throw label.",
                              "No official diagrams or shot counts enter the source-only selection.",
                              "Counter absence does not prove a false event."]}
    MANIFEST.write_text(json.dumps(result, indent=2) + "\n")
    print({"candidates": len(records), "sheets": 3, "output": str(OUTDIR)})


if __name__ == "__main__":
    main()
