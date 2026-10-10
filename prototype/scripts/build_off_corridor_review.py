"""Render source-only frames around every full-match corridor-withheld candidate."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
VIDEO = BASE / "source-360p.mp4"
CORRIDOR = BASE / "full-match-stage1-corridor-postscore.json"
OUTPUT = BASE / "off-corridor-source-review"
FRAME_OFFSETS_S = (0.0, 5.0)
THUMBNAIL_SIZE = (480, 270)
ROWS_PER_SHEET = 8


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    data = json.loads(CORRIDOR.read_text())
    withheld = sorted(data["withheld_events"], key=lambda row: row["crossing_time_s"])
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {VIDEO}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    sheets = []
    samples = []
    for sheet_index, start in enumerate(range(0, len(withheld), ROWS_PER_SHEET), start=1):
        subset = withheld[start : start + ROWS_PER_SHEET]
        tile_w, tile_h = THUMBNAIL_SIZE
        sheet = Image.new("RGB", (tile_w * 2, (tile_h + 26) * len(subset)), "white")
        draw = ImageDraw.Draw(sheet)
        for row_index, candidate in enumerate(subset):
            candidate_id = candidate["id"]
            crossing_s = candidate["crossing_time_s"]
            for column, offset_s in enumerate(FRAME_OFFSETS_S):
                requested_s = crossing_s + offset_s
                cap.set(cv2.CAP_PROP_POS_MSEC, requested_s * 1000)
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f"Cannot read {candidate_id} at {requested_s:.3f} s")
                frame_index = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
                thumbnail = cv2.resize(frame, THUMBNAIL_SIZE, interpolation=cv2.INTER_AREA)
                px, py = column * tile_w, row_index * (tile_h + 26)
                sheet.paste(
                    Image.fromarray(cv2.cvtColor(thumbnail, cv2.COLOR_BGR2RGB)), (px, py + 26)
                )
                draw.text(
                    (px + 4, py + 5),
                    f"{candidate_id}  {requested_s:.1f}s  frame {frame_index}",
                    fill="black",
                )
                samples.append(
                    {
                        "candidate_id": candidate_id,
                        "crossing_time_s": crossing_s,
                        "offset_s": offset_s,
                        "requested_source_time_s": requested_s,
                        "decoded_frame_index": frame_index,
                        "approx_decoded_source_time_s": frame_index / fps,
                        "sheet": f"sheet-{sheet_index:02d}.jpg",
                        "sheet_row": row_index,
                        "sheet_column": column,
                    }
                )
        name = f"sheet-{sheet_index:02d}.jpg"
        sheet.save(OUTPUT / name, quality=88)
        sheets.append(name)
    cap.release()
    (OUTPUT / "manifest.json").write_text(
        json.dumps(
            {
                "status": "source_only_review_frames_no_event_labels",
                "source_sha256": digest(VIDEO),
                "corridor_sha256": digest(CORRIDOR),
                "source_fps": fps,
                "withheld_candidate_count": len(withheld),
                "candidate_ids": [row["id"] for row in withheld],
                "frame_offsets_s": FRAME_OFFSETS_S,
                "sheets": sheets,
                "samples": samples,
                "limitations": [
                    "Two stills per candidate cannot establish complete interval recall or physical throw identity.",
                    "This prediction-selected packet is not an independent blind ground-truth set.",
                ],
            },
            indent=2,
        )
        + "\n"
    )
    print(f"Rendered {len(withheld)} candidates in {len(sheets)} sheets")


if __name__ == "__main__":
    main()
