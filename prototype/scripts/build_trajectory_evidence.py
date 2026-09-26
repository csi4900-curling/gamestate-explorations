"""Render existing frozen manual labels and saved predictions on source frames."""

from pathlib import Path
import json, cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / "trajectory-accuracy"
data = json.loads((out / "results.json").read_text())
cap = cv2.VideoCapture(str(ROOT / "continuous/clip.mp4"))
for r in data["rows"]:
    t = r["time_s"]
    cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * 30))
    ok, f = cap.read()
    if not ok:
        raise RuntimeError(t)
    x, y = r["reference_pixel"]
    left = x - 60
    top = y - 45
    scale = 6
    crop = Image.fromarray(
        cv2.cvtColor(f[top : top + 90, left : left + 120], cv2.COLOR_BGR2RGB)
    ).resize((720, 540), Image.Resampling.NEAREST)
    sheet = Image.new("RGB", (1440, 640), "#f5f2e9")
    sheet.paste(crop, (0, 80))
    sheet.paste(crop, (720, 80))
    d = ImageDraw.Draw(sheet)
    d.text(
        (20, 15),
        f"{t}s | Frame {t * 30} | Source 1920 x 1080 | Zoom x6, nearest pixels",
        fill="#173b38",
    )
    d.text((20, 42), "IMAGE SOURCE SANS MARQUE", fill="#173b38")
    d.text(
        (740, 42),
        "ROUGE + : estimation manuelle IA | BLEU cercle : detection OpenCV",
        fill="#173b38",
    )
    a = (720 + (x - left) * scale, 80 + (y - top) * scale)
    p = r["prediction"]["pixel"]
    b = (720 + (p[0] - left) * scale, 80 + (p[1] - top) * scale)
    d.line([a, b], fill="white", width=3)
    d.line((a[0] - 12, a[1], a[0] + 12, a[1]), fill="#e02030", width=2)
    d.line((a[0], a[1] - 12, a[0], a[1] + 12), fill="#e02030", width=2)
    d.ellipse((b[0] - 6, b[1] - 6, b[0] + 6, b[1] + 6), outline="#007fff", width=2)
    d.text(
        (740, 625),
        f"Manuel ({x}, {y}) | Auto ({p[0]:.4f}, {p[1]:.4f}) | Ecart {r['pixel_error']:.4f} px",
        fill="#173b38",
    )
    sheet.save(out / f"comparison-{t}.png")
cap.release()
