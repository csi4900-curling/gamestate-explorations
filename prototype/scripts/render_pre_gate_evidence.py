"""Show original video crops beside unchanged detector-coordinate overlays."""

from pathlib import Path
import cv2, json
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / "pre-gate-audit"
data = json.loads((out / "results.json").read_text())
cap = cv2.VideoCapture(str(ROOT / "throw-analysis/end3.mp4"))
fps = cap.get(cv2.CAP_PROP_FPS)
for row in data["throws"]:
    pts = row["points"]
    chosen = [pts[0], pts[len(pts) // 2], pts[-1]]
    sheet = Image.new("RGB", (1440, 700), "#f5f2e9")
    d = ImageDraw.Draw(sheet)
    for i, p in enumerate(chosen):
        cap.set(cv2.CAP_PROP_POS_FRAMES, round((p["time_s"] - 1650) * fps))
        ok, f = cap.read()
        if not ok:
            raise RuntimeError(p["time_s"])
        x, y = [v * 3 for v in p["pixel"]]
        left = round(x) - 60
        top = max(0, round(y) - 40)
        crop = Image.fromarray(
            cv2.cvtColor(f[top : top + 80, left : left + 120], cv2.COLOR_BGR2RGB)
        ).resize((480, 320), Image.Resampling.NEAREST)
        sheet.paste(crop, (i * 480, 35))
        sheet.paste(crop, (i * 480, 370))
        px = i * 480 + (x - left) * 4
        py = 370 + (y - top) * 4
        d.ellipse((px - 8, py - 8, px + 8, py + 8), outline="#00bf90", width=2)
        d.text(
            (i * 480 + 8, 10),
            f"{row['id']} source {p['time_s']:.1f}s | pixel 640x360 {p['pixel']}",
            fill="#173b38",
        )
    d.text(
        (10, 355),
        "Haut : image source. Bas : point du detecteur agrandi x3 puis crop x4. Aucun point manuel.",
        fill="#173b38",
    )
    sheet.save(out / (row["id"] + "-source.jpg"))
cap.release()
