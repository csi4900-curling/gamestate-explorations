"""Render frozen China registration transitions against original source frames."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from scripts.audit_china_2022_cap_continuation_scale_transfer import (  # noqa: E402
    reconstructed_tracks,
)

BASE = ROOT / "validation/official-shot-sequence"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
CATALOG = BASE / "china-global-shot-scoped-cap-motion-first.json"
TRANSFER = BASE / "china-ice-region-cap-track-registration-transfer-development.json"
OUT = BASE / "china-registration-transfer-source-probe"


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("China registration source packet already exists")
    catalog = json.loads(CATALOG.read_text())
    transfer = json.loads(TRANSFER.read_text())
    if catalog["source_video_sha256"] != transfer["source_video_sha256"] or transfer[
        "source_video_sha256"
    ] != digest(VIDEO):
        raise ValueError("China source lineage differs")
    rows = transfer["rows"]
    ice_lost = [
        row
        for row in rows
        if row["subframe_cue"] == "sustained_camera_relative_motion_cue"
        and row["ice_region_cue"] != "sustained_camera_relative_motion_cue"
    ]
    ice_gained = [
        row
        for row in rows
        if row["subframe_cue"] != "sustained_camera_relative_motion_cue"
        and row["ice_region_cue"] == "sustained_camera_relative_motion_cue"
    ]
    short_gained = [
        row
        for row in rows
        if row["direct_cue"] != "sustained_camera_relative_motion_cue"
        and row["subframe_cue"] == "sustained_camera_relative_motion_cue"
    ]
    ice_lost.sort(key=lambda row: row["episode_id"])
    for group in (ice_gained, short_gained):
        group.sort(key=lambda row: (-row["span_px"], row["episode_id"]))
    chosen = []
    for label, group in (
        ("all_ice_region_losses", ice_lost),
        ("top_four_ice_region_gains", ice_gained[:4]),
        ("top_four_short_pair_gains", short_gained[:4]),
    ):
        for row in group:
            if row["episode_id"] not in {item["episode_id"] for item in chosen}:
                chosen.append({**row, "selection": label})
    shot_by_id = {shot["camera_shot_id"]: shot for shot in catalog["shots"]}
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        raise ValueError("China source unreadable")
    fps = capture.get(cv2.CAP_PROP_FPS)
    OUT.mkdir(parents=True)
    sheets = []
    try:
        for row in chosen:
            eid = row["episode_id"]
            shot = shot_by_id[row["camera_shot_id"]]
            points = reconstructed_tracks(capture, fps, shot)[eid]
            sheet = Image.new("RGB", (1280, 1520), "white")
            for index, point in enumerate(points[-2:]):
                capture.set(cv2.CAP_PROP_POS_FRAMES, round(point["time_s"] * fps))
                ok, frame = capture.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise ValueError(f"Frame unreadable: {eid}")
                image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                image = image.resize((1280, 720), Image.Resampling.NEAREST)
                x, y = (round(2 * v) for v in point["pixel"])
                ImageDraw.Draw(image).ellipse(
                    (x - 16, y - 16, x + 16, y + 16), outline="#00ecff", width=4
                )
                pane = Image.new("RGB", (1280, 760), "white")
                pane.paste(image, (0, 40))
                ImageDraw.Draw(pane).text(
                    (12, 12),
                    f"{eid} t={point['time_s']:.1f}s {row['selection']} "
                    f"{row['direct_cue']} / {row['subframe_cue']} / "
                    f"{row['ice_region_cue']}",
                    fill="black",
                )
                sheet.paste(pane, (0, 760 * index))
            filename = eid.lower() + "-source.jpg"
            sheet.save(OUT / filename, quality=91)
            sheets.append(
                {
                    "episode_id": eid,
                    "selection": row["selection"],
                    "span_px": row["span_px"],
                    "sheet": filename,
                    "sheet_sha256": digest(OUT / filename),
                }
            )
    finally:
        capture.release()
    (OUT / "manifest.json").write_text(
        json.dumps(
            {
                "status": "fixed_transition_source_packet_not_independent_labels",
                "source_video_sha256": transfer["source_video_sha256"],
                "catalog_sha256": digest(CATALOG),
                "transfer_sha256": digest(TRANSFER),
                "runner_sha256": digest(Path(__file__)),
                "selection": "All ice-region sustained-cue losses; four largest-span new ice-region sustained cues; four largest-span new short-pair sustained cues. Deduplicate IDs in that order before viewing frames.",
                "selection_group_sizes": {
                    "ice_region_losses": len(ice_lost),
                    "ice_region_gains": len(ice_gained),
                    "short_pair_gains": len(short_gained),
                },
                "sheets": sheets,
            },
            indent=2,
        )
        + "\n"
    )
    print(
        json.dumps(
            {
                "sheets": len(sheets),
                "ice_losses": len(ice_lost),
                "ice_gains": len(ice_gained),
                "short_gains": len(short_gained),
            }
        )
    )


if __name__ == "__main__":
    main()
