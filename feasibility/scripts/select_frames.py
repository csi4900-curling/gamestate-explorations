from pathlib import Path
import cv2
from PIL import Image, ImageDraw

r = Path(__file__).resolve().parents[1]
c = cv2.VideoCapture(str(r / "sources/cbc_2018_final_full.mp4"))
times = [
    100,
    148,
    166,
    168,
    195,
    196,
    231,
    233,
    267,
    269,
    271,
    309,
    344,
    369,
    371,
    373,
    398,
    414,
    449,
    451,
    469,
    470,
    471,
]
for t in times:
    c.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, f = c.read()
    if ok:
        cv2.imwrite(str(r / f"frames/t{t:03d}.png"), f)
        cv2.imwrite(str(r / f"frames/t{t:03d}_960.png"), cv2.resize(f, (960, 540)))
sheet = Image.new("RGB", (1440, 270 * 8), "#18202c")
for i, t in enumerate(times):
    im = Image.open(r / f"frames/t{t:03d}_960.png").resize((480, 270))
    sheet.paste(im, ((i % 3) * 480, (i // 3) * 270))
    ImageDraw.Draw(sheet).text(
        ((i % 3) * 480 + 5, (i // 3) * 270 + 5),
        str(t),
        fill="white",
        stroke_width=2,
        stroke_fill="black",
    )
sheet.save(r / "frames/selection.jpg")
