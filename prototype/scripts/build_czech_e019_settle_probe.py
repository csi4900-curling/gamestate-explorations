"""Render dense original-resolution source crops across E019's settle gap."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
VIDEO = BASE / "source-1080p-full-format270.mp4"
MOTION = BASE / "full-match-motion-merged-postscore.json"
BOARD = BASE / "full-match-partial-boards-postscore.json"
OUT = BASE / "e019-settle-continuity-source-probe"
TIMES = (686.0, 686.25, 686.5, 686.75, 687.0, 687.25, 687.5, 688.0)
CROP = (1270, 350, 1450, 530)


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("E019 source probe already exists")
    motion = json.loads(MOTION.read_text())
    boards = json.loads(BOARD.read_text())
    video_hash = digest(VIDEO)
    if (
        motion["high_resolution_source_sha256"] != video_hash
        or boards["high_resolution_source_sha256"] != video_hash
    ):
        raise ValueError("E019 high-resolution source lineage differs")
    path = next(r for r in motion["rows"] if r["candidate_id"] == "S20")["selection"]["path"]
    board = next(r for r in boards["rows"] if r["candidate_id"] == "S20")
    by_time = {p["source_time_s"]: p["pixel_center"] for p in path}
    board_by_time = {
        f["source_time_s"]: [s for s in f["stones"] if s["colour"] == "red"]
        for f in board["frames"]
    }
    if (
        board["tail"]["start_s"] != 687.0
        or 686.5 not in by_time
        or len(board_by_time.get(687.0, [])) != 1
    ):
        raise ValueError("E019 endpoint or first board frame changed")
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not capture.isOpened() or abs(fps - 30) > 0.01:
        raise ValueError("E019 source unreadable or frame rate changed")
    OUT.mkdir(parents=True)
    sheet = Image.new("RGB", (720, 1440), "white")
    samples = []
    try:
        for index, time in enumerate(TIMES):
            frame_number = round(time * fps)
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ok, frame = capture.read()
            if not ok or frame.shape[:2] != (1080, 1920):
                raise ValueError(f"E019 source frame unreadable: {time}")
            source = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            crop = source.crop(CROP).resize((360, 360), Image.Resampling.NEAREST)
            draw = ImageDraw.Draw(crop)
            draw.rectangle((0, 0, 170, 26), fill="white")
            draw.text((5, 7), f"source {time:.2f} s", fill="black")
            markers = []
            if time in by_time:
                x, y = by_time[time]
                px, py = 2 * (x - CROP[0]), 2 * (y - CROP[1])
                draw.ellipse((px - 24, py - 24, px + 24, py + 24), outline="lime", width=3)
                markers.append({"kind": "moving_path_center", "pixel_1080": [x, y]})
            for stone in board_by_time.get(time, []):
                x, y = stone["pixel_center"]
                px, py = 2 * (x - CROP[0]), 2 * (y - CROP[1])
                draw.ellipse((px - 31, py - 31, px + 31, py + 31), outline="magenta", width=3)
                markers.append({"kind": "board_red_detection", "pixel_1080": [x, y]})
            col, row = index % 2, index // 2
            sheet.paste(crop, (col * 360, row * 360))
            samples.append(
                {
                    "source_time_s_requested": time,
                    "decoded_frame_index": frame_number,
                    "source_time_s_frame": round(frame_number / fps, 6),
                    "markers": markers,
                }
            )
    finally:
        capture.release()
    sheet.save(OUT / "dense-contact-sheet.jpg", quality=95)
    manifest = {
        "status": "e019_original_source_settle_gap_probe_not_identity_truth",
        "source_video_sha256": video_hash,
        "input_sha256": {"motion": digest(MOTION), "board": digest(BOARD)},
        "runner_sha256": digest(Path(__file__)),
        "crop_full_frame_1080": list(CROP),
        "marker_legend": {
            "lime": "stored S20 moving-path center",
            "magenta": "stored S20 board-frame red detection",
        },
        "samples": samples,
        "sheet_sha256": digest(OUT / "dense-contact-sheet.jpg"),
        "limitations": [
            "The quarter-second requested times round to the nearest 30 fps source frame; manifest records the exact frame used.",
            "Markers come from different processing stages and do not establish one persistent physical stone identity.",
            "The crop omits other stones and players outside this local image region; collision context requires the full frame.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"frames": len(samples), "sheet": str(OUT / "dense-contact-sheet.jpg")}))


if __name__ == "__main__":
    main()
