"""Render source frames for span-ranked Norway ice-context decisions."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation"
VIDEO = BASE / "throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
CONTEXT = BASE / "official-shot-sequence/norway-cap-track-ice-context-development.json"
CATALOG = BASE / "official-shot-sequence/norway-global-shot-scoped-cap-motion-first.json"
OUT = BASE / "official-shot-sequence/norway-cap-ice-context-source-probe"


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Norway ice-context source probe already exists")
    context = json.loads(CONTEXT.read_text())
    catalog = json.loads(CATALOG.read_text())
    if context["source_video_sha256"] != digest(VIDEO):
        raise ValueError("Source/context lineage differs")
    spans = {
        track["episode_id"]: track["span_px"]
        for shot in catalog["shots"]
        for track in shot["tracks"]
    }
    chosen = []
    for accepted in (False, True):
        matches = [
            row
            for row in context["rows"]
            if row["prior_area_next_step_status"] == "unique_motion_gate_choice"
            and row["exploratory_both_rings_below_0p30"] is accepted
        ]
        matches.sort(key=lambda row: (-spans[row["episode_id"]], row["episode_id"]))
        chosen.extend(matches[:4])
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        raise ValueError("Norway source unreadable")
    OUT.mkdir(parents=True)
    sheets = []
    try:
        for row in chosen:
            sheet = Image.new("RGB", (1280, 760 * 2), "white")
            for index, sample in enumerate(row["samples"]):
                capture.set(cv2.CAP_PROP_POS_FRAMES, sample["decoded_frame_index"])
                ok, frame = capture.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise ValueError("Norway source frame unreadable")
                pane = Image.new("RGB", (1280, 760), "white")
                image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                image = image.resize((1280, 720), Image.Resampling.NEAREST)
                draw = ImageDraw.Draw(image)
                x, y = (round(2 * n) for n in sample["cap_center_px_360"])
                draw.ellipse((x - 16, y - 16, x + 16, y + 16), outline="#00ecff", width=4)
                draw.rectangle((x - 56, y - 80, x + 56, y + 80), outline="#ff00dd", width=3)
                pane.paste(image, (0, 40))
                ImageDraw.Draw(pane).text(
                    (12, 12),
                    f"{row['episode_id']} t={sample['time_s']:.1f} "
                    f"ring nonice={sample['nonice_ring_fraction']:.3f} "
                    f"under nonice={sample['underpoint_nonice_fraction']}",
                    fill="black",
                )
                sheet.paste(pane, (0, 760 * index))
            filename = row["episode_id"].lower() + "-source.jpg"
            sheet.save(OUT / filename, quality=91)
            sheets.append(
                {
                    "episode_id": row["episode_id"],
                    "span_px": spans[row["episode_id"]],
                    "ring_gate_passes": row["exploratory_both_rings_below_0p30"],
                    "sheet": filename,
                    "sheet_sha256": digest(OUT / filename),
                }
            )
    finally:
        capture.release()
    (OUT / "manifest.json").write_text(
        json.dumps(
            {
                "status": "span_ranked_source_review_packet_not_independent_labels",
                "source_video_sha256": context["source_video_sha256"],
                "context_sha256": digest(CONTEXT),
                "catalog_sha256": digest(CATALOG),
                "runner_sha256": digest(Path(__file__)),
                "selection": "Four largest catalog spans among unique relative-area next steps failing both-ring <0.30, plus four largest among passing steps; selected without source-frame viewing.",
                "marker_legend": "cyan ring: cap center; magenta box: non-ice ring outer extent",
                "sheets": sheets,
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps({"sheets": len(sheets), "output": str(OUT)}))


if __name__ == "__main__":
    main()
