"""Recreate manual annotation contact sheets; never imported by inference. Run from project root."""

import cv2
from PIL import Image, ImageDraw
from pathlib import Path

out = Path("prototype/throw-analysis/evidence")
cap = cv2.VideoCapture("prototype/sources/canada-korea-2024-360p.mp4")
for start in range(1650, 2760, 180):
    sheet = Image.new("RGB", (6 * 320, 6 * 185), "#102832")
    d = ImageDraw.Draw(sheet)
    for i, t in enumerate(range(start, min(start + 180, 2760), 5)):
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, f = cap.read()
        if not ok:
            continue
        im = Image.fromarray(cv2.cvtColor(f[:160, :320], cv2.COLOR_BGR2RGB))
        x = i % 6 * 320
        y = i // 6 * 185
        sheet.paste(im, (x, y + 25))
        d.text((x + 8, y + 6), str(t), fill="white")
    sheet.save(out / f"manual-{start}.jpg", quality=94)
cap.release()

import cv2
from PIL import Image, ImageDraw
from pathlib import Path

centres = [
    1738,
    1790,
    1839,
    1896,
    1949,
    2008,
    2053,
    2104,
    2178,
    2252,
    2303,
    2360,
    2428,
    2478,
    2638,
    2689,
]
cap = cv2.VideoCapture("prototype/sources/canada-korea-2024-360p.mp4")
out = Path("prototype/throw-analysis/evidence")
for n, c in enumerate(centres, 1):
    sheet = Image.new("RGB", (6 * 280, 2 * 282), "#102832")
    d = ImageDraw.Draw(sheet)
    for i, t in enumerate(range(c - 5, c + 7)):
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, f = cap.read()
        if not ok:
            continue
        im = Image.fromarray(cv2.cvtColor(f[:130, 80:220], cv2.COLOR_BGR2RGB)).resize((280, 260))
        x = i % 6 * 280
        y = i // 6 * 282
        sheet.paste(im, (x, y + 22))
        d.text((x + 8, y + 5), f"{n:02} / {t}s", fill="white")
        d.line((x, y + 22 + 120, x + 280, y + 22 + 120), fill="#36a0b0", width=1)
    sheet.save(out / f"event-reference-{n:02}.jpg", quality=95)
cap.release()
