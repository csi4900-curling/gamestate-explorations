"""Source-image evidence near provisional settling; not endpoint ground truth."""

from pathlib import Path
import cv2, json
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / "throw-segments"
data = json.loads((out / "results.json").read_text())
cap = cv2.VideoCapture(str(ROOT / "throw-analysis/end3.mp4"))
fps = cap.get(cv2.CAP_PROP_FPS)
for s in data["segments"]:
    t = s["settling"].get("confirmed_at_s")
    if t is None:
        continue
    sheet = Image.new("RGB", (1440, 380), "#f5f2e9")
    d = ImageDraw.Draw(sheet)
    for i, offset in enumerate([-2, 0, 2]):
        sample = t + offset
        cap.set(cv2.CAP_PROP_POS_FRAMES, round((sample - 1650) * fps))
        ok, f = cap.read()
        if not ok:
            raise RuntimeError(sample)
        crop = Image.fromarray(cv2.cvtColor(f[300:900, 960:1920], cv2.COLOR_BGR2RGB)).resize(
            (480, 300)
        )
        sheet.paste(crop, (i * 480, 45))
        d.text(
            (i * 480 + 8, 12),
            f"{s['id']} source {sample:.1f}s | candidate {offset:+d}s",
            fill="#173b38",
        )
    d.text(
        (10, 360),
        "Images source : controle visuel, aucune annotation independante de fin physique.",
        fill="#173b38",
    )
    sheet.save(out / (s["id"] + "-endpoint.jpg"))
cap.release()
