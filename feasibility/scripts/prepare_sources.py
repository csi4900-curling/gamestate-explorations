"""Download public sources (if missing) and reconstruct the selected inputs.
Run from any directory. Existing full video/PDF are reused. No credentials required.
"""

from pathlib import Path
import json, subprocess, sys, hashlib
import requests
import cv2
from PIL import Image
import pyreadr
import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "sources"
SRC.mkdir(exist_ok=True)
COMMIT = (SRC / "CurlR_commit.txt").read_text().strip()
URL = "https://www.youtube.com/watch?v=qqXEvKF-lM8"
PDF = "https://curlit.com/PDF/OWG2018_ResultsBook.pdf"


def download(url, path):
    if path.exists():
        return
    with requests.get(url, timeout=(30, 180), stream=True) as r:
        r.raise_for_status()
        with path.with_suffix(path.suffix + ".part").open("wb") as f:
            for b in r.iter_content(1 << 20):
                f.write(b)
    path.with_suffix(path.suffix + ".part").replace(path)


video = SRC / "cbc_2018_final_full.mp4"
if not video.exists():
    subprocess.run(
        [sys.executable, "-m", "yt_dlp", "-f", "137", "--no-progress", "-o", str(video), URL],
        check=True,
    )
download(PDF, SRC / "OWG2018_ResultsBook.pdf")
download(
    f"https://raw.githubusercontent.com/ritchi12/CurlR/{COMMIT}/data/mxd_shots.rda",
    SRC / "mxd_shots.rda",
)
x = pyreadr.read_r(str(SRC / "mxd_shots.rda"))["mxd_shots"]
x[(x.ID == "OWG2018") & (x.Game == 1)].to_csv(SRC / "owg2018_final_records.csv", index=False)
download(
    "https://worldcurling.org/wp-content/uploads/2025/08/Rules-2025.pdf", SRC / "Rules-2025.pdf"
)
cap = cv2.VideoCapture(str(video))
ann = json.loads((ROOT / "annotations/manual.json").read_text())
manifest = []
for t in sorted(set([f["timestamp_s"] for f in ann["frames"]] + [230, 232])):
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, frame = cap.read()
    if not ok:
        raise RuntimeError(f"Cannot decode at {t}s")
    cv2.imwrite(str(ROOT / f"frames/t{t:03d}.png"), frame)
    if t in [136, 194, 230, 232]:
        Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).resize((960, 540)).save(
            ROOT / f"frames/t{t:03d}_960.png"
        )
    else:
        cv2.imwrite(str(ROOT / f"frames/t{t:03d}_960.png"), cv2.resize(frame, (960, 540)))
    manifest.append(
        dict(
            requested_timestamp_s=t,
            decoded_timestamp_s=cap.get(cv2.CAP_PROP_POS_MSEC) / 1000,
            decoded_frame_index=int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1,
            width=frame.shape[1],
            height=frame.shape[0],
        )
    )
cap.release()
(ROOT / "sources/frame_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
p = fitz.open(SRC / "OWG2018_ResultsBook.pdf")
folder = SRC / "official_shot_diagrams"
folder.mkdir(exist_ok=True)
for end in range(1, 7):
    page = p[1200 + end]
    items = []
    page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).save(SRC / f"official_end{end}.png")
    for img in page.get_images(full=True):
        if img[2:4] == (300, 600):
            rect = page.get_image_rects(img[0])[0]
            items.append((round(rect.y0), rect.x0, img[0]))
    for shot, (_, _, xref) in enumerate(sorted(items)):
        d = p.extract_image(xref)
        (folder / f"end{end}_shot{shot}.{d['ext']}").write_bytes(d["image"])
provenance = dict(
    video=dict(
        url=URL,
        title="Mixed Doubles Curling Final : Canada vs. Switzerland | Pyeongchang 2018",
        publisher="CBC Sports",
        format_id="137",
        local_file=video.name,
        note="Edited highlights, not an uninterrupted match. Timestamps refer to this upload.",
    ),
    official_pdf=dict(url=PDF, pages_one_based=list(range(1202, 1208))),
    curlr=dict(
        url="https://github.com/ritchi12/CurlR",
        commit=COMMIT,
        licence="CC0-1.0",
        filter="ID == 'OWG2018', Game == 1",
        coordinate_note="Extracted diagram pixels; not metres; stone number is detection order.",
    ),
    geometry=dict(
        url="https://worldcurling.org/wp-content/uploads/2025/08/Rules-2025.pdf",
        radii_m=[1.829, 1.219, 0.610],
        note="Nominal marked radii; actual paint geometry not surveyed.",
    ),
    retrieval_session_date="2026-09-23",
    media_rights="Video and PDF retain source owners’ rights. CurlR CC0 does not extend to footage. Local research copy; no public redistribution performed.",
)
for key, path in [("video", video), ("official_pdf", SRC / "OWG2018_ResultsBook.pdf")]:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    provenance[key]["sha256"] = h.hexdigest()
(SRC / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
print("Prepared source records, original diagrams, frames, timestamps and hashes.")
