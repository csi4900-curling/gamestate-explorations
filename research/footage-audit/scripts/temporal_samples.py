from pathlib import Path
import json, subprocess, concurrent.futures, re
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
CASES = [("qn9tHfcimlQ", 3677), ("Oj5FD5FTVNc", 1922), ("peXfdw6Veo0", 3772), ("dcb_DCtBW-4", 8322)]


def run(case):
    vid, start = case
    d = json.loads((ROOT / "metadata" / f"{vid}.raw.json").read_text())
    f = max(
        [
            f
            for f in d["formats"]
            if f.get("protocol") == "https"
            and str(f.get("vcodec", "")).startswith("avc1")
            and f.get("height", 0) <= 1080
        ],
        key=lambda f: f["height"],
    )
    folder = ROOT / "frames" / vid / f"sequence-{start}"
    folder.mkdir(exist_ok=True)
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-rw_timeout",
        "20000000",
        "-ss",
        str(start),
        "-i",
        f["url"],
        "-t",
        "12",
        "-vf",
        "fps=1/2",
        "-q:v",
        "2",
        "-y",
        str(folder / "%02d.jpg"),
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        err = (
            re.sub(r"https?://\S+", "[media URL omitted]", r.stderr)[-500:]
            if r.returncode
            else None
        )
    except subprocess.TimeoutExpired:
        err = "90-second download timeout"
    images = sorted(folder.glob("*.jpg"))
    sheet = Image.new("RGB", (1000, 3 * 310 + 45), "#142c3a")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=16)
    draw.text((10, 10), f"{vid} | 12-second temporal probe from {start}s", font=font, fill="white")
    for i, p in enumerate(images[:6]):
        im = Image.open(p)
        im.thumbnail((490, 276))
        x = i % 2 * 500
        y = i // 2 * 310 + 45
        sheet.paste(im, (x + (500 - im.width) // 2, y))
        draw.text(
            (x + 10, y + 280),
            f"Sample {i + 1} | nominal window +{i * 2} to +{i * 2 + 2}s",
            font=font,
            fill="white",
        )
    sheet.save(ROOT / "contact-sheets" / f"{vid}-temporal.jpg", quality=90)
    return {
        "id": vid,
        "start_s": start,
        "window_s": 12,
        "sampling": "fps=1/2; labels show nominal two-second bins, not exact source PTS",
        "frames": [str(p.relative_to(ROOT)) for p in images],
        "error": err,
    }


with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    out = list(pool.map(run, CASES))
(ROOT / "temporal-manifest.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
