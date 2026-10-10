"""Render source frames for gained and lost Norway cap-area decisions."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation"
VIDEO = BASE / "throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
TRANSFER = BASE / "official-shot-sequence/norway-2022-cap-area-gate-transfer-development.json"
OUT = BASE / "official-shot-sequence/norway-2022-cap-area-source-probe"
IDS = ("S28-Y01", "S304-R01", "S321-R01")


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Norway source probe already exists")
    transfer = json.loads(TRANSFER.read_text())
    if transfer["source_video_sha256"] != digest(VIDEO):
        raise ValueError("Norway source/transfer lineage differs")
    by_id = {r["episode_id"]: r for r in transfer["rows"]}
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise ValueError("Norway source unreadable")
    OUT.mkdir(parents=True)
    sheets = []
    try:
        for eid in IDS:
            row = by_id[eid]
            points = row["last_two_reconstructed_points_360"]
            times = [points[0]["time_s"], points[1]["time_s"], row["next_sample_time_s"]]
            sheet = Image.new("RGB", (1280, 2280), "white")
            for index, time in enumerate(times):
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(time * 30))
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise ValueError(f"Norway source frame unreadable: {eid}")
                image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                image = image.resize((1280, 720), Image.Resampling.NEAREST)
                draw = ImageDraw.Draw(image)
                if index < 2:
                    x, y = (2 * v for v in points[index]["pixel"])
                    draw.ellipse((x - 16, y - 16, x + 16, y + 16), outline="#00ecff", width=4)
                else:
                    x0, y0, x1, y1 = row["search_roi_xyxy_px_360"]
                    draw.rectangle((2 * x0, 2 * y0, 2 * x1, 2 * y1), outline="#00ecff", width=3)
                    for ordinal, component in enumerate(row["raw_colour_components"], start=1):
                        x, y = (2 * v for v in component["centroid_px_1080"])
                        draw.ellipse((x - 14, y - 14, x + 14, y + 14), outline="#ff00dd", width=4)
                        draw.text(
                            (x + 16, y - 10),
                            f"{ordinal}: {component['area_px2']:.0f}px2",
                            fill="#ff00dd",
                            stroke_width=2,
                            stroke_fill="white",
                        )
                pane = Image.new("RGB", (1280, 760), "white")
                pane.paste(image, (0, 40))
                ImageDraw.Draw(pane).text(
                    (12, 12),
                    f"{eid} source {time:.1f}s | "
                    + ("stored cap" if index < 2 else "next-frame raw components"),
                    fill="black",
                )
                sheet.paste(pane, (0, index * 760))
            filename = eid.lower() + "-source.jpg"
            sheet.save(OUT / filename, quality=93)
            sheets.append(
                {
                    "episode_id": eid,
                    "sheet": filename,
                    "sheet_sha256": digest(OUT / filename),
                    "sample_times_s": times,
                    "absolute_status": row["absolute_area_decision"]["status"],
                    "past_area_status": row["past_cap_area_0p5_to_2_decision"]["status"],
                }
            )
    finally:
        cap.release()
    manifest = {
        "status": "same_agent_norway_cap_area_source_review_packet",
        "source_video_sha256": transfer["source_video_sha256"],
        "transfer_sha256": digest(TRANSFER),
        "runner_sha256": digest(Path(__file__)),
        "sheets": sheets,
        "marker_legend": "cyan ring: prior cap center; cyan rectangle: next search ROI; magenta ring: next raw colour component with source-pixel contour area",
        "limitations": [
            "Three selected source cases illustrate gains and losses; they cannot estimate physical stone precision or recall.",
            "The source and visual judgments were exposed during development and are not independent identity labels.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"sheets": len(sheets), "output": str(OUT)}))


if __name__ == "__main__":
    main()
