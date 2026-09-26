from pathlib import Path
import json, subprocess, concurrent.futures, re
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
records = json.loads((ROOT / "catalogue-sample.json").read_text())
fractions = [0.08, 0.20, 0.32, 0.44, 0.56, 0.68, 0.80, 0.92]
font = (
    ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    if Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf").exists()
    else ImageFont.load_default(size=16)
)


def sample(rec):
    vid = rec["id"]
    d = json.loads((ROOT / "metadata" / f"{vid}.raw.json").read_text())
    formats = [
        f
        for f in d["formats"]
        if f.get("protocol") == "https"
        and str(f.get("vcodec", "")).startswith("avc1")
        and f.get("height", 0) <= 1080
    ]
    if not formats:
        return {"id": vid, "error": "No direct AVC format"}
    f = max(formats, key=lambda f: f.get("height", 0))
    folder = ROOT / "frames" / vid
    folder.mkdir(exist_ok=True)
    frames = []
    for fraction in fractions:
        t = round(rec["duration_s"] * fraction)
        path = folder / f"{t:05d}.jpg"
        if not path.exists():
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-rw_timeout",
                "20000000",
                "-ss",
                str(t),
                "-i",
                f["url"],
                "-frames:v",
                "1",
                "-q:v",
                "2",
                "-y",
                str(path),
            ]
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=55)
                error = (
                    re.sub(r"https?://\S+", "[media URL omitted]", r.stderr)[-700:]
                    if r.returncode
                    else None
                )
            except subprocess.TimeoutExpired:
                error = "Timed out after 55 seconds"
        else:
            error = None
        frames.append(
            {
                "requested_timestamp_s": t,
                "fraction": fraction,
                "file": str(path.relative_to(ROOT)) if path.exists() else None,
                "error": error,
            }
        )
        print(vid, t, "ok" if path.exists() else "FAILED", flush=True)
    result = {
        "id": vid,
        "format_id": f["format_id"],
        "width": f.get("width"),
        "height": f.get("height"),
        "fps": f.get("fps"),
        "frames": frames,
        "sampling_note": "Eight fixed fractions across each recording, not handpicked successes. Timestamps requested via ffmpeg seeking; not independently frame-index verified.",
    }
    (ROOT / "metadata" / f"{vid}.frames.json").write_text(json.dumps(result, indent=2) + "\n")
    sheet = Image.new("RGB", (1000, 4 * 310 + 55), "#142c3a")
    draw = ImageDraw.Draw(sheet)
    draw.text((14, 12), vid + " | " + rec["selection_reason"], font=font, fill="white")
    for i, item in enumerate(frames):
        x = (i % 2) * 500
        y = 55 + (i // 2) * 310
        if item["file"]:
            im = Image.open(ROOT / item["file"])
            im.thumbnail((490, 276))
            sheet.paste(im, (x + (500 - im.width) // 2, y))
        draw.text(
            (x + 10, y + 280),
            f"{item['requested_timestamp_s'] // 60:02d}:{item['requested_timestamp_s'] % 60:02d} | {int(item['fraction'] * 100)}%"
            + (" | FAILED" if not item["file"] else ""),
            font=font,
            fill="white",
        )
    sheet.save(ROOT / "contact-sheets" / f"{vid}.jpg", quality=90)
    return result


if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(sample, records))
    (ROOT / "frame-manifest.json").write_text(json.dumps(results, indent=2) + "\n")
