"""Expose the earliest observed motion without inventing physical release time."""

import json
from pathlib import Path
from statistics import median

import cv2
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "prototype/throw-analysis/predictions.json"
VIDEO = ROOT / "prototype/continuous/clip.mp4"
OUT = ROOT / "prototype/throw-analysis"
IMAGE = OUT / "T11-release-visibility.jpg"
JSON = OUT / "observed-onset-v1.json"
SOURCE_START_S = 2260.0


def build_contact_sheet():
    rows = [
        (2303.200, "Avant : pierre masquée ou ambiguë"),
        (2303.333, "Apparition partielle"),
        (2303.433, "Pierre séparée et en mouvement"),
        (2303.500, "Premier point du suivi figé"),
        (2303.967, "Franchissement de la ligne virtuelle"),
    ]
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise FileNotFoundError(VIDEO)
    tile_w, tile_h = 720, 440
    canvas = Image.new("RGB", (tile_w * 3, tile_h * 2 + 66), "#f7f6f1")
    draw = ImageDraw.Draw(canvas)
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    font = ImageFont.truetype(font_path, 20)
    small = ImageFont.truetype(font_path, 16)
    for index, (source_s, caption) in enumerate(rows):
        cap.set(cv2.CAP_PROP_POS_FRAMES, round((source_s - SOURCE_START_S) * 30))
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"Cannot decode source frame at {source_s}")
        # Crop within the known departure panel so the occlusion is inspectable.
        panel = Image.fromarray(cv2.cvtColor(frame[100:640, 220:780], cv2.COLOR_BGR2RGB))
        panel = panel.resize((tile_w, 405), Image.Resampling.LANCZOS)
        x, y = index % 3 * tile_w, index // 3 * tile_h
        canvas.paste(panel, (x, y + 35))
        draw.text((x + 10, y + 7), f"{source_s:.3f} s · {caption}", fill="#14313c", font=font)
    cap.release()
    draw.text(
        (15, tile_h * 2 + 18),
        "La séparation entre la pierre et le dispositif de lancer reste cachée ; ces temps ne mesurent pas le lâcher physique.",
        fill="#53676c",
        font=small,
    )
    canvas.save(IMAGE, quality=91)


def main():
    source = json.loads(SOURCE.read_text())
    events = source["events"]
    assert len(events) == 16 and source["source_interval_s"] == [1650, 2760]
    rows = []
    for event in events:
        first = event["first_observed_s"]
        crossing = event["crossing_time_s"]
        assert first < crossing and event["release_time_s"] is None
        assert event["trajectory"][0]["time_s"] == first
        rows.append(
            {
                "id": event["id"],
                "colour": event["colour"],
                "first_observed_track_s": first,
                "virtual_line_crossing_s": crossing,
                "pre_line_lead_s": round(crossing - first, 3),
                "physical_release_s": None,
                "time_semantics": "first observation of a track later confirmed as moving; not separation from the delivery device",
            }
        )
    t11 = next(row for row in rows if row["id"] == "T11")
    assert t11["first_observed_track_s"] == 2303.5
    assert abs(t11["virtual_line_crossing_s"] - 2303.956) < 0.001
    t11["source_frame_review"] = {
        "last_ambiguous_or_occluded_s": 2303.333,
        "first_clearly_separable_moving_stone_s": 2303.433,
        "physical_release_s": None,
        "reason": "The player occludes separation from the delivery device; the first separable stone is already moving.",
        "evidence_image": IMAGE.name,
        "scope": "Selected T11 retrospective source-frame review, not a detector accuracy score.",
    }
    leads = [row["pre_line_lead_s"] for row in rows]
    artifact = {
        "source": source["source"],
        "source_interval_s": source["source_interval_s"],
        "event_count": len(rows),
        "median_pre_line_lead_s": round(median(leads), 3),
        "lead_range_s": [min(leads), max(leads)],
        "physical_release_verified_count": 0,
        "interpretation": "The frozen tracker already sees the moving stone before the line. These earlier onsets improve review timing but do not identify exact physical release.",
        "events": rows,
    }
    JSON.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n")
    build_contact_sheet()
    print(f"Wrote {JSON} and {IMAGE}")


if __name__ == "__main__":
    main()
