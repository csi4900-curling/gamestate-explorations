from pathlib import Path
import json, cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / "cross-view"
data = json.loads((out / "results.json").read_text())
cap = cv2.VideoCapture(str(ROOT / "throw-analysis/end3.mp4"))
fps = cap.get(cv2.CAP_PROP_FPS)
for row in data["throws"]:
    if not row["departure"] or not row["arrival"]:
        continue
    receiving = row.get("display_arrival", row["arrival"])
    pts = [
        row["departure"][0],
        row["departure"][-1],
        receiving[0],
        min(row["arrival"], key=lambda p: abs(p["time_s"] - row["receiving_hog_crossing_s"])),
    ]
    labels = [
        "Depart : debut visible",
        "Depart : derniere observation",
        "Reception : premiere position affichee"
        if row["id"] == "T11"
        else "Reception : premiere observation",
        "Reception : proche hog line",
    ]
    sheet = Image.new("RGB", (1440, 700), "#f5f2e9")
    d = ImageDraw.Draw(sheet)
    for i, (p, label) in enumerate(zip(pts, labels)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, round((p["time_s"] - 1650) * fps))
        ok, f = cap.read()
        if not ok:
            raise RuntimeError(p["time_s"])
        x, y = p["pixel"]
        left = round(x) - 90
        top = max(0, round(y) - 65)
        if row["id"] == "T11" and i == 2:
            top = min(1080 - 130, top)
        crop = Image.fromarray(
            cv2.cvtColor(f[top : top + 130, left : left + 180], cv2.COLOR_BGR2RGB)
        ).resize((360, 260))
        sheet.paste(crop, (i * 360, 65))
        sheet.paste(crop, (i * 360, 380))
        d.text((i * 360 + 7, 10), row["id"] + " " + label, fill="#173b38")
        d.text((i * 360 + 7, 32), f"Source {p['time_s']:.2f}s", fill="#173b38")
        px = i * 360 + (x - left) * 2
        py = 380 + (y - top) * 2
        d.ellipse(
            (px - 7, py - 7, px + 7, py + 7), outline="#00bf90" if i < 2 else "#f9a500", width=2
        )
    d.text(
        (10, 350),
        "Haut : source sans marque. Bas : centre detecte. Identite inter-camera provisoire, pas une reference independante.",
        fill="#173b38",
    )
    sheet.save(out / (row["id"] + "-evidence.jpg"))
cap.release()
