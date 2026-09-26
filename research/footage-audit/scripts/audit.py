"""Read-only source audit. Fetch metadata; sample remote media without full downloads."""

from pathlib import Path
import concurrent.futures, csv, json, subprocess, sys
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parents[1]
CAT = ROOT.parent / "sources/provided-video-catalogue.csv"
SELECTION = [
    ("qn9tHfcimlQ", "Paralympic broadcast"),
    ("Oj5FD5FTVNc", "2022 competition / Us"),
    ("RCX3H1JyEJs", "Mixed-doubles minigames"),
    ("Hen_cn-mbG0", "Four-player training"),
    ("9Hzj5P0PLOw", "Shared recording / Richmond"),
    ("peXfdw6Veo0", "Stadium source / Leduc"),
    ("aWXo6XeUFQw", "2024 championship"),
    ("dcb_DCtBW-4", "2025 shared recording"),
]


def videoid(url):
    p = urlparse(url)
    return p.path.strip("/") if p.netloc == "youtu.be" else parse_qs(p.query).get("v", [None])[0]


rows = list(csv.DictReader(CAT.open()))


def metadata(item):
    vid, reason = item
    p = ROOT / "metadata" / f"{vid}.raw.json"
    err = ROOT / "metadata" / f"{vid}.stderr.txt"
    if "--refresh" in sys.argv or not p.exists() or not p.stat().st_size:
        with p.open("w") as out, err.open("w") as e:
            try:
                subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "yt_dlp",
                        "--skip-download",
                        "--no-playlist",
                        "--socket-timeout",
                        "20",
                        "--retries",
                        "1",
                        "--dump-single-json",
                        f"https://www.youtube.com/watch?v={vid}",
                    ],
                    stdout=out,
                    stderr=e,
                    timeout=100,
                )
            except subprocess.TimeoutExpired:
                e.write("\nMetadata timeout after 100 seconds\n")
    try:
        d = json.loads(p.read_text())
    except (ValueError, FileNotFoundError):
        d = {}
    rec = {
        "id": vid,
        "selection_reason": reason,
        "catalogue_rows": [r for r in rows if videoid(r["video_url"]) == vid],
        "url": f"https://www.youtube.com/watch?v={vid}",
        "metadata_ok": bool(d),
        "title": d.get("title"),
        "duration_s": d.get("duration"),
        "uploader": d.get("uploader"),
        "width": d.get("width"),
        "height": d.get("height"),
        "fps": d.get("fps"),
        "availability": d.get("availability"),
        "max_available_height": max(
            [f.get("height") or 0 for f in d.get("formats", [])], default=0
        ),
    }
    (ROOT / "metadata" / f"{vid}.json").write_text(json.dumps(rec, indent=2) + "\n")
    return rec


if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(metadata, SELECTION))
    (ROOT / "catalogue-sample.json").write_text(json.dumps(results, indent=2) + "\n")
    for r in results:
        print(r["id"], r["metadata_ok"], r["duration_s"], r["title"])
