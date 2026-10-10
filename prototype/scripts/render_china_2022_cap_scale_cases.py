"""Show original 2022 frames for three cap-scale failure diagnoses."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation"
VIDEO = BASE / "throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
AUDIT = BASE / "official-shot-sequence/china-2022-cap-continuation-scale-transfer-development.json"
OUT = BASE / "official-shot-sequence/china-2022-cap-scale-source-probe"
IDS = ("S28-R01", "S86-R01", "S230-Y01")


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("2022 source probe already exists")
    audit = json.loads(AUDIT.read_text())
    if audit["source_video_sha256"] != digest(VIDEO):
        raise ValueError("2022 source/audit lineage differs")
    by_id = {r["episode_id"]: r for r in audit["rows"]}
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise ValueError("2022 source unreadable")
    OUT.mkdir(parents=True)
    sheets = []
    try:
        for eid in IDS:
            row = by_id[eid]
            points = row["last_two_reconstructed_points_360"]
            times = [points[0]["time_s"], points[1]["time_s"], row["next_sample_time_s"]]
            frames = []
            for index, time in enumerate(times):
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(time * 30))
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise ValueError("2022 source frame unreadable")
                image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                image = image.resize((1280, 720), Image.Resampling.NEAREST)
                draw = ImageDraw.Draw(image)
                if index < 2:
                    x, y = points[index]["pixel"]
                    x, y = 2 * x, 2 * y
                    draw.ellipse((x - 16, y - 16, x + 16, y + 16), outline="#00ecff", width=4)
                else:
                    x0, y0, x1, y1 = row["search_roi_xyxy_px_360"]
                    draw.rectangle((2 * x0, 2 * y0, 2 * x1, 2 * y1), outline="#00ecff", width=3)
                    for ordinal, component in enumerate(row["raw_colour_components"], start=1):
                        x, y = component["centroid_px_1080"]
                        x, y = 2 * x, 2 * y
                        draw.ellipse((x - 14, y - 14, x + 14, y + 14), outline="#ff00dd", width=4)
                        draw.text(
                            (x + 17, y - 8),
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
                frames.append(pane)
            sheet = Image.new("RGB", (1280, 3 * 760), "white")
            for i, image in enumerate(frames):
                sheet.paste(image, (0, i * 760))
            filename = eid.lower().replace("-", "-") + "-source.jpg"
            sheet.save(OUT / filename, quality=93)
            sheets.append(
                {
                    "episode_id": eid,
                    "sheet": filename,
                    "sheet_sha256": digest(OUT / filename),
                    "sample_times_s": times,
                    "raw_next_component_areas_px2_360": [
                        c["area_px2"] for c in row["raw_colour_components"]
                    ],
                }
            )
    finally:
        cap.release()
    manifest = {
        "status": "same_agent_2022_cap_scale_source_review_packet",
        "source_video_sha256": audit["source_video_sha256"],
        "scale_audit_sha256": digest(AUDIT),
        "runner_sha256": digest(Path(__file__)),
        "sheets": sheets,
        "marker_legend": "cyan ring: previous frozen cap center; cyan rectangle: next search ROI; magenta ring: every next-frame raw colour component with source-pixel contour area",
        "limitations": [
            "Three selected source cases diagnose failure modes; they do not estimate physical stone precision or recall.",
            "Source pixels and cap tracks were already exposed to development, so visual judgments are not independent labels.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"sheets": len(sheets), "output": str(OUT)}))


if __name__ == "__main__":
    main()
