"""Render the intervals that caused selected China registration motion cues."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from scripts.audit_china_2022_cap_continuation_scale_transfer import (  # noqa: E402
    reconstructed_tracks)

BASE = ROOT / "validation/official-shot-sequence"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
CATALOG = BASE / "china-global-shot-scoped-cap-motion-first.json"
TRANSFER = BASE / "china-ice-region-cap-track-registration-transfer-development.json"
OUT = BASE / "china-registration-motion-interval-source-probe"
SELECTED = {
    "S307-R01": (4079.0, 4083.0),
    "S230-Y01": (2863.0, 2867.0),
    "S45-R01": (620.0, 624.0),
    "S86-R01": (1214.0, 1218.0),
    "S412-R01": (5568.0, 5570.0),
}


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Motion-interval source packet already exists")
    catalog = json.loads(CATALOG.read_text())
    transfer = json.loads(TRANSFER.read_text())
    if (catalog["source_video_sha256"] !=
            transfer["source_video_sha256"] or
            transfer["source_video_sha256"] != digest(VIDEO)):
        raise ValueError("Source lineage differs")
    shots = {shot["camera_shot_id"]: shot for shot in catalog["shots"]}
    rows = {row["episode_id"]: row for row in transfer["rows"]}
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise ValueError("Source unreadable")
    fps = cap.get(cv2.CAP_PROP_FPS)
    OUT.mkdir(parents=True)
    sheets = []
    try:
        for eid, times in SELECTED.items():
            row = rows[eid]
            points = reconstructed_tracks(cap, fps,
                                           shots[row["camera_shot_id"]])[eid]
            by_time = {point["time_s"]: point for point in points}
            sheet = Image.new("RGB", (1280, 1520), "white")
            for index, time in enumerate(times):
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(time * fps))
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise ValueError(f"Source frame unreadable: {eid} {time}")
                image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                image = image.resize((1280, 720), Image.Resampling.NEAREST)
                x, y = (round(2 * v) for v in by_time[time]["pixel"])
                ImageDraw.Draw(image).ellipse(
                    (x-16, y-16, x+16, y+16), outline="#00ecff", width=4)
                pane = Image.new("RGB", (1280, 760), "white")
                pane.paste(image, (0, 40))
                ImageDraw.Draw(pane).text(
                    (12, 12), f"{eid} source {time:.1f}s", fill="black")
                sheet.paste(pane, (0, 760 * index))
            filename = eid.lower() + "-motion.jpg"
            sheet.save(OUT / filename, quality=91)
            sheets.append({
                "episode_id": eid,
                "sample_times_s": times,
                "sheet": filename,
                "sheet_sha256": digest(OUT / filename),
                "subframe_cue": row["subframe_cue"],
                "ice_region_cue": row["ice_region_cue"],
            })
    finally:
        cap.release()
    (OUT / "manifest.json").write_text(json.dumps({
        "status": "post_result_selected_motion_interval_source_packet",
        "source_video_sha256": transfer["source_video_sha256"],
        "catalog_sha256": digest(CATALOG),
        "transfer_sha256": digest(TRANSFER),
        "runner_sha256": digest(Path(__file__)),
        "selection": "After result inspection: four largest-span new short-pair cues at their earliest consecutive high-residual run, plus the single ice-region loss at its first whole-frame high-residual run. Source examples only, not independent accuracy labels.",
        "sheets": sheets,
    }, indent=2) + "\n")
    print(json.dumps({"sheets": len(sheets)}))


if __name__ == "__main__":
    main()
