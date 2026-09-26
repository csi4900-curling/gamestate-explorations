from pathlib import Path
import cv2
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
cap = cv2.VideoCapture(str(root / "sources/cbc_2018_final_full.mp4"))
sets = [
    [132, 134, 136, 138, 148, 150, 152, 154, 170, 172, 174, 176],
    [188, 190, 192, 194, 230, 232, 234, 236, 270, 272, 274, 276],
    [302, 304, 306, 308, 342, 344, 346, 348, 370, 372, 374, 376],
    [394, 396, 398, 400, 412, 414, 416, 418, 450, 452, 454, 456, 472, 474, 476, 478],
]
for k, times in enumerate(sets):
    sheet = Image.new("RGB", (1440, 270 * ((len(times) + 2) // 3)), "#18202c")
    for i, t in enumerate(times):
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, f = cap.read()
        if not ok:
            continue
        cv2.imwrite(str(root / f"frames/t{t:03d}.png"), f)
        im = Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB)).resize((480, 270))
        sheet.paste(im, ((i % 3) * 480, (i // 3) * 270))
        ImageDraw.Draw(sheet).text(
            ((i % 3) * 480 + 5, (i // 3) * 270 + 5),
            str(t),
            fill="white",
            stroke_width=2,
            stroke_fill="black",
        )
    sheet.save(root / f"frames/detail_{k}.jpg")
