from pathlib import Path
import cv2
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
cap = cv2.VideoCapture(str(root / "sources/cbc_2018_final_full.mp4"))
times = list(range(0, 540, 10))
for batch in range(3):
    sheet = Image.new("RGB", (1280, 810), "#18202c")
    for i, t in enumerate(times[batch * 18 : (batch + 1) * 18]):
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            continue
        im = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        im.thumbnail((320, 225))
        x = (i % 4) * 320
        y = (i // 4) * 162
        im = im.resize((288, 162))
        sheet.paste(im, (x, y))
        ImageDraw.Draw(sheet).text(
            (x + 5, y + 5), f"{t}s", fill="white", stroke_width=2, stroke_fill="black"
        )
    sheet.save(root / f"frames/contact_{batch}.jpg")
