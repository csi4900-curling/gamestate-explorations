"""Render source frames for all lost and span-ranked gained motion cues."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/official-shot-sequence"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
CATALOG = BASE / "norway-global-shot-scoped-cap-motion-first.json"
TRANSFER = BASE / "norway-2022-cap-area-gate-transfer-development.json"
AUDIT = BASE / "norway-ice-region-cap-track-registration-development.json"
OUT = BASE / "norway-ice-region-registration-source-probe"


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Source packet already exists")
    catalog = json.loads(CATALOG.read_text())
    transfer = json.loads(TRANSFER.read_text())
    audit = json.loads(AUDIT.read_text())
    if not (catalog["source_video_sha256"] ==
            transfer["source_video_sha256"] ==
            audit["source_video_sha256"] == digest(VIDEO)):
        raise ValueError("Norway source lineage differs")
    spans = {track["episode_id"]: track["span_px"]
             for shot in catalog["shots"] for track in shot["tracks"]}
    endpoints = {row["episode_id"]: row["last_two_reconstructed_points_360"]
                 for row in transfer["rows"]}
    lost = [row for row in audit["rows"]
            if row["whole_frame_subframe_cue"] ==
            "sustained_camera_relative_motion_cue" and
            row["ice_region_cue"] != "sustained_camera_relative_motion_cue"]
    gained = [row for row in audit["rows"]
              if row["whole_frame_subframe_cue"] !=
              "sustained_camera_relative_motion_cue" and
              row["ice_region_cue"] == "sustained_camera_relative_motion_cue"]
    lost.sort(key=lambda row: row["episode_id"])
    gained.sort(key=lambda row: (-spans[row["episode_id"]],
                                 row["episode_id"]))
    chosen = lost + gained[:4]
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        raise ValueError("Norway source unreadable")
    OUT.mkdir(parents=True)
    sheets = []
    try:
        for row in chosen:
            eid = row["episode_id"]
            sheet = Image.new("RGB", (1280, 1520), "white")
            for index, point in enumerate(endpoints[eid]):
                capture.set(cv2.CAP_PROP_POS_FRAMES,
                            round(point["time_s"] * 30))
                ok, frame = capture.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise ValueError(f"Frame unreadable: {eid}")
                image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                image = image.resize((1280, 720), Image.Resampling.NEAREST)
                x, y = (round(2 * v) for v in point["pixel"])
                ImageDraw.Draw(image).ellipse(
                    (x-16, y-16, x+16, y+16), outline="#00ecff", width=4)
                pane = Image.new("RGB", (1280, 760), "white")
                pane.paste(image, (0, 40))
                ImageDraw.Draw(pane).text((12, 12),
                    f"{eid} t={point['time_s']:.1f}s "
                    f"whole={row['whole_frame_subframe_cue']} "
                    f"ice={row['ice_region_cue']}", fill="black")
                sheet.paste(pane, (0, 760 * index))
            filename = eid.lower() + "-source.jpg"
            sheet.save(OUT / filename, quality=91)
            sheets.append({"episode_id": eid,
                           "selection": "lost" if row in lost else "gained",
                           "span_px": spans[eid],
                           "sheet": filename,
                           "sheet_sha256": digest(OUT / filename)})
    finally:
        capture.release()
    (OUT / "manifest.json").write_text(json.dumps({
        "status": "source_review_packet_not_independent_labels",
        "source_video_sha256": audit["source_video_sha256"],
        "catalog_sha256": digest(CATALOG),
        "transfer_sha256": digest(TRANSFER),
        "audit_sha256": digest(AUDIT),
        "runner_sha256": digest(Path(__file__)),
        "selection": "All three previously sustained paths losing that cue, plus four largest-span newly sustained paths; selected by frozen audit status and catalog span before frame viewing.",
        "sheets": sheets,
    }, indent=2) + "\n")
    print(json.dumps({"lost": len(lost),
                      "gained_reviewed": min(4, len(gained)),
                      "source_sheets": len(sheets)}))


if __name__ == "__main__":
    main()
