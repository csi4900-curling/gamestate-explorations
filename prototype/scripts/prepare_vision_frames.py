from pathlib import Path
import json, subprocess, concurrent.futures, shutil, re

ROOT = Path(__file__).resolve().parents[1]
target = ROOT / "vision/frames"
target.mkdir(exist_ok=True)
d = json.loads((ROOT / "vision/source-metadata.raw.json").read_text())
f = next(f for f in d["formats"] if f["format_id"] == "137")
audit = ROOT.parent / "research/footage-audit/frames/aWXo6XeUFQw"
for p in audit.glob("*.jpg"):
    shutil.copy2(p, target / p.name)


def run(t):
    p = target / f"{t:05d}.jpg"
    if not p.exists():
        r = subprocess.run(
            [
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
                str(p),
            ],
            capture_output=True,
            text=True,
            timeout=70,
        )
        if r.returncode:
            raise RuntimeError(re.sub(r"https?://\S+", "[media URL]", r.stderr))
    return {
        "timestamp_s": t,
        "file": p.name,
        "width": 1920,
        "height": 1080,
        "source": "https://www.youtube.com/watch?v=aWXo6XeUFQw",
        "format_id": "137",
    }


with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    out = list(pool.map(run, [750, 1900, 2300, 4000, 6000, 7800]))
for p in sorted(audit.glob("*.jpg")):
    out.append(
        {
            "timestamp_s": int(p.stem),
            "file": p.name,
            "width": 1920,
            "height": 1080,
            "source": "https://www.youtube.com/watch?v=aWXo6XeUFQw",
            "format_id": "137",
            "reused_audit_frame": True,
        }
    )
(ROOT / "vision/frame-manifest.json").write_text(json.dumps(out, indent=2) + "\n")
print(len(out), "original-resolution frames prepared")
