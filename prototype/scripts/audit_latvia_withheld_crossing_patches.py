"""Preserve source-pixel reviews of every withheld Latvia left crossing."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
PACKET_DIR = BASE / "withheld-left-crossing-patch-packet"
PACKET = PACKET_DIR / "manifest.json"
SCORE = BASE / "withheld-left-crossing-patch-score-development.json"
VIDEO = BASE / "source-360p.mp4"
OUT = BASE / "withheld-left-crossing-patch-source-audit"
AMBIGUOUS_IDS = {"R01-S99", "R01-S117"}


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    packet = json.loads(PACKET.read_text())
    score = json.loads(SCORE.read_text())
    if (
        len(packet["rows"]) != 47
        or len(score["rows"]) != 47
        or packet["source_video_sha256"] != digest(VIDEO)
        or score["packet_manifest_sha256"] != digest(PACKET)
    ):
        raise ValueError("Withheld packet, score, and source video differ")
    scores = {row["event_id"]: row for row in score["rows"]}
    if len(scores) != 47:
        raise ValueError("Duplicate scored crossing IDs")
    if {row["event_id"] for row in packet["rows"]} != set(scores):
        raise ValueError("Packet and score crossing inventories differ")
    OUT.mkdir(parents=True, exist_ok=True)
    rows, pages = [], []
    for start in range(0, 47, 8):
        chunk = packet["rows"][start : start + 8]
        page_index = start // 8 + 1
        sheet = Image.new("RGB", (576, 192 * len(chunk)), "white")
        draw = ImageDraw.Draw(sheet)
        for local_index, packet_row in enumerate(chunk):
            event_id = packet_row["event_id"]
            crop_hashes = []
            if len(packet_row["samples"]) != 3:
                raise ValueError(f"Unexpected sample count: {event_id}")
            for sample_index, sample in enumerate(packet_row["samples"]):
                crop = PACKET_DIR / sample["crop_path"]
                if digest(crop) != sample["crop_sha256"]:
                    raise ValueError(f"Crop fingerprint mismatch: {crop}")
                image = Image.open(crop).convert("RGB")
                if image.size != (48, 48):
                    raise ValueError(f"Unexpected crop geometry: {crop}")
                sheet.paste(
                    image.resize((192, 192), Image.Resampling.NEAREST),
                    (sample_index * 192, local_index * 192),
                )
                crop_hashes.append(sample["crop_sha256"])
            score_row = scores[event_id]
            y = local_index * 192
            draw.rectangle((0, y, 136, y + 20), fill="white")
            draw.text((3, y + 3), f"{event_id} {score_row['mean_score']:.2f}", fill="red")
            pixel_class = (
                "ambiguous_low_red_pixels_near_wheelchair"
                if event_id in AMBIGUOUS_IDS
                else "person_or_equipment_pixels_in_crossing_crops"
            )
            if packet_row["source_review"] == "person_pixels" and event_id in AMBIGUOUS_IDS:
                raise ValueError(f"Prior review conflicts: {event_id}")
            if packet_row["source_review"] == "ambiguous_pixels" and event_id not in AMBIGUOUS_IDS:
                raise ValueError(f"Prior review conflicts: {event_id}")
            rows.append(
                {
                    "candidate_id": event_id,
                    "frozen_patch_mean_score": score_row["mean_score"],
                    "frozen_patch_model_positive": score_row["predicted_stone_like"],
                    "source_pixel_class": pixel_class,
                    "class_origin": "same_agent_postscore_crossing_crop_review",
                    "physical_throw_verified": False,
                    "sampling_policy": packet_row["sampling_policy"],
                    "review_page": f"withheld-page-{page_index}.jpg",
                    "crop_sha256": crop_hashes,
                }
            )
        page = OUT / f"withheld-page-{page_index}.jpg"
        sheet.save(page, quality=90)
        pages.append({"image": page.name, "sha256": digest(page), "candidate_count": len(chunk)})
    counts = Counter(row["source_pixel_class"] for row in rows)
    if counts != {
        "person_or_equipment_pixels_in_crossing_crops": 45,
        "ambiguous_low_red_pixels_near_wheelchair": 2,
    }:
        raise ValueError("Withheld source-pixel class counts changed")
    manifest = {
        "status": "postscore_all_withheld_source_pixel_review_not_throw_truth",
        "selection": "all 47 withheld raw Latvia left crossings",
        "source_video_sha256": digest(VIDEO),
        "packet_manifest_sha256": digest(PACKET),
        "score_sha256": digest(SCORE),
        "runner_sha256": digest(Path(__file__)),
        "source_class_counts": dict(counts),
        "model_positive_count": sum(row["frozen_patch_model_positive"] for row in rows),
        "rows": rows,
        "pages": pages,
        "limitations": [
            "Source-pixel classes were assigned after model scoring by the same development agent, not an independent annotator.",
            "Three crossing-local crops classify the tracked image object, not every object elsewhere in the source frame.",
            "One short track uses nearest observed samples instead of symmetric crossing samples.",
            "No crop class verifies a physical throw, and this review does not estimate full-match throw-event recall.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    print(dict(counts))


if __name__ == "__main__":
    main()
