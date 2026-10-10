"""Render matched-size frozen-model stone patch successes and misses."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw

from sys import path as sys_path
ROOT = Path(__file__).resolve().parents[2]
sys_path.insert(0, str(ROOT / "prototype"))
from cap_patch_verifier import context_bbox

BASE = ROOT / "validation/throw-event-benchmark"
LAT = BASE / "canada-latvia-2024"
IT = BASE / "canada-italy"
LAT_SCORE = LAT / "full-right-reviewed-frozen-sideview-patch-transfer-development.json"
IT_SCORE = BASE / "right-visual-cue-pair-estonia-italy-development.json"
OUT = LAT / "latvia-italy-frozen-patch-contrast"
CASES = (
    ("latvia", "one_second_greedy:A004:1", "yellow_stone_model_negative"),
    ("italy", "A016", "yellow_stone_model_positive"),
    ("latvia", "two_second_global:A184:1", "red_stone_model_negative"),
    ("italy", "A024", "red_stone_model_positive"),
)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    lat_score = json.loads(LAT_SCORE.read_text())
    it_score = json.loads(IT_SCORE.read_text())
    scans = {
        "one_second_greedy": json.loads((LAT / "full-right-area-first-transfer.json").read_text()),
        "two_second_global": json.loads((LAT / "full-right-global-area-development.json").read_text()),
    }
    videos = {"latvia": LAT / "source-360p.mp4", "italy": IT / "source.mp4"}
    if (lat_score["source_video_sha256"] != digest(videos["latvia"]) or
            it_score["input_sha256"]["italy"]["video"] != digest(videos["italy"])):
        raise ValueError("Source videos differ")
    if OUT.exists():
        raise ValueError("Contrast packet exists")
    OUT.mkdir(parents=True)
    rows = []
    for page_index, start in enumerate((0, 2), 1):
        sheet = Image.new("RGB", (960, 1120), "white")
        for row_index, (recording, track_id, selection) in enumerate(
                CASES[start:start + 2]):
            if recording == "latvia":
                score = next(r for r in lat_score["rows"] if r[
                    "proposal_id"] == track_id)
                variant, raw, _ = track_id.split(":")
                proposal = next(r for r in scans[variant][
                    "directional_review_proposals"] if r["raw_track_id"] == raw)
                points = {p["time_s"]: p for p in proposal[
                    "observed_prefix_points"]}
                samples = score["sample_scores"]
            else:
                score = next(r for r in it_score["rows"] if r[
                    "recording"] == "italy" and r["raw_track_id"] == track_id)
                samples = score["patch_samples"]
            capture = cv2.VideoCapture(str(videos[recording]), cv2.CAP_FFMPEG,
                                       [cv2.CAP_PROP_N_THREADS, 1])
            fps = capture.get(cv2.CAP_PROP_FPS)
            if not capture.isOpened() or fps <= 0:
                raise ValueError("Source unreadable")
            details = []
            try:
                for sample_index, sample in enumerate(samples):
                    time = sample["time_s"]
                    bbox = (points[time]["bbox"] if recording == "latvia"
                            else sample["cap_bbox_px"])
                    capture.set(cv2.CAP_PROP_POS_FRAMES, round(time * fps))
                    ok, frame = capture.read()
                    if not ok or frame.shape[:2] != (360, 640):
                        raise ValueError("Source frame unreadable")
                    source = Image.fromarray(cv2.cvtColor(frame,
                                                           cv2.COLOR_BGR2RGB))
                    panel = source.crop((320, 0, 640, 360))
                    draw = ImageDraw.Draw(panel)
                    x, y, w, h = bbox
                    draw.rectangle((x - 320, y, x + w - 320, y + h),
                                   outline="magenta", width=3)
                    bx, by, side, _ = context_bbox(bbox)
                    draw.rectangle((bx - 320, by, bx + side - 320, by + side),
                                   outline="cyan", width=2)
                    draw.rectangle((0, 0, 270, 24), fill="white")
                    draw.text((3, 4), f"{track_id} {time:.0f}s {sample['patch_score']:+.2f}",
                              fill="black")
                    crop = source.crop((bx, by, bx + side, by + side))
                    crop = crop.resize((192, 192), Image.Resampling.NEAREST)
                    left, top = sample_index * 320, row_index * 560
                    sheet.paste(panel, (left, top))
                    sheet.paste(crop, (left + 64, top + 360))
                    details.append({"time_s": time, "cap_bbox_px": bbox,
                                    "model_context_bbox_px": [bx, by, side, side],
                                    "patch_score": sample["patch_score"]})
            finally:
                capture.release()
            rows.append({"recording": recording, "track_id": track_id,
                         "selection": selection, "source_samples": details,
                         "page": f"page-{page_index}.jpg"})
        sheet.save(OUT / f"page-{page_index}.jpg", quality=94)
    result = {
        "status": "selected_frozen_patch_visual_contrast_not_causal_explanation",
        "source_video_sha256": {name: digest(path) for name, path in videos.items()},
        "input_sha256": {"latvia_scores": digest(LAT_SCORE),
                         "estonia_italy_scores": digest(IT_SCORE),
                         "latvia_one_second_scan": digest(LAT / "full-right-area-first-transfer.json"),
                         "latvia_global_scan": digest(LAT / "full-right-global-area-development.json")},
        "context_geometry_code_sha256": digest(ROOT / "prototype/cap_patch_verifier.py"),
        "runner_sha256": digest(Path(__file__)),
        "rows": rows,
        "page_sha256": {p.name: digest(p) for p in OUT.glob("page-*.jpg")},
        "limitations": [
            "Four cases were chosen after scores were known; the packet is diagnostic, not a test set.",
            "Appearance differences in these frames do not establish which factor caused the model-score gap.",
            "None of these patch scores confirms a physical delivery or full trajectory.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"cases": len(rows), "pages": len(result["page_sha256"])}))


if __name__ == "__main__":
    main()
