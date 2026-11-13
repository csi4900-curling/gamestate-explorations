"""Preserve source-pixel reviews of every frozen-negative accepted Latvia crossing."""

from hashlib import sha256
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
SCORE = BASE / "all-accepted-left-crossing-patch-score-development.json"
PACKET = BASE / "all-accepted-left-crossing-patch-packet/manifest.json"
VIDEO = BASE / "source-360p.mp4"
OUT = BASE / "all-negative-patch-source-audit"
NEGATIVE_IDS = (
    "R01-S15",
    "R01-S05",
    "R01-S105",
    "R01-S13",
    "R01-S54",
    "R01-S61",
    "R01-S50",
    "R01-S119",
    "R01-S108",
    "R01-S73",
    "R01-S45",
    "R01-S11",
    "R01-S19",
    "R01-S21",
    "R01-S66",
    "R01-S53",
    "R01-S14",
    "R01-S17",
    "R01-S31",
    "R01-S49",
    "R01-S68",
    "R01-S12",
    "R01-S98",
    "R01-S57",
    "R01-S35",
    "R01-S64",
    "R01-S27",
    "R01-S41",
    "R01-S92",
    "R01-S37",
    "R01-S16",
    "R01-S80",
    "R01-S93",
    "R01-S36",
)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    score = json.loads(SCORE.read_text())
    packet = json.loads(PACKET.read_text())
    if (
        score["packet_manifest_sha256"] != digest(PACKET)
        or len(packet["sources"]) != 1
        or packet["sources"][0]["video_sha256"] != digest(VIDEO)
        or not packet["sources"][0]["same_video_bytes_as_timeline"]
    ):
        raise ValueError("Score, packet, and Latvia source fingerprints differ")
    negatives = sorted(
        (row for row in score["rows"] if not row["predicted_stone_like"]),
        key=lambda row: (row["mean_score"], row["event_id"]),
    )
    if tuple(row["event_id"] for row in negatives) != NEGATIVE_IDS:
        raise ValueError("Frozen negative crossing inventory changed")
    by_id = {row["event_id"]: row for row in packet["rows"]}
    OUT.mkdir(parents=True, exist_ok=True)
    rows, pages = [], []
    for page_index in range(4):
        chunk = negatives[page_index * 9 : (page_index + 1) * 9]
        sheet = Image.new("RGB", (576, 192 * len(chunk)), "white")
        draw = ImageDraw.Draw(sheet)
        for local_index, score_row in enumerate(chunk):
            event_id = score_row["event_id"]
            packet_row = by_id[event_id]
            crop_hashes = []
            for sample_index, sample in enumerate(packet_row["samples"]):
                crop = BASE / "all-accepted-left-crossing-patch-packet" / sample["crop_path"]
                if digest(crop) != sample["crop_sha256"]:
                    raise ValueError(f"Crop hash mismatch: {crop}")
                image = Image.open(crop).convert("RGB")
                if image.size != (48, 48):
                    raise ValueError(f"Unexpected crop geometry: {crop}")
                sheet.paste(
                    image.resize((192, 192), Image.Resampling.NEAREST),
                    (sample_index * 192, local_index * 192),
                )
                crop_hashes.append(sample["crop_sha256"])
            y = local_index * 192
            draw.rectangle((0, y, 132, y + 20), fill="white")
            draw.text((3, y + 3), f"{event_id} {score_row['mean_score']:.2f}", fill="red")
            if event_id == "R01-S45":
                pixel_class = "person_head_pixels"
            elif event_id == "R01-S119":
                pixel_class = "ambiguous_yellow_pixels_near_player"
            else:
                pixel_class = "stone_body_pixels_in_crossing_crops"
            rows.append(
                {
                    "candidate_id": event_id,
                    "frozen_patch_mean_score": score_row["mean_score"],
                    "source_pixel_class": pixel_class,
                    "class_origin": "same_agent_postscore_crossing_crop_review",
                    "physical_throw_verified": False,
                    "review_page": f"negative-page-{page_index + 1}.jpg",
                    "crop_sha256": crop_hashes,
                }
            )
        page = OUT / f"negative-page-{page_index + 1}.jpg"
        sheet.save(page, quality=90)
        pages.append({"image": page.name, "sha256": digest(page), "candidate_count": len(chunk)})
    counts = {
        "stone_body_pixels_in_crossing_crops": sum(
            row["source_pixel_class"] == "stone_body_pixels_in_crossing_crops" for row in rows
        ),
        "person_head_pixels": sum(
            row["source_pixel_class"] == "person_head_pixels" for row in rows
        ),
        "ambiguous_yellow_pixels_near_player": sum(
            row["source_pixel_class"] == "ambiguous_yellow_pixels_near_player" for row in rows
        ),
    }
    if counts != {
        "stone_body_pixels_in_crossing_crops": 32,
        "person_head_pixels": 1,
        "ambiguous_yellow_pixels_near_player": 1,
    }:
        raise ValueError("Source review counts changed")
    manifest = {
        "status": "postscore_all_negative_source_pixel_review_not_throw_truth",
        "selection": "all 34 frozen-model-negative accepted left crossings",
        "source_video_sha256": digest(VIDEO),
        "score_sha256": digest(SCORE),
        "packet_manifest_sha256": digest(PACKET),
        "runner_sha256": digest(Path(__file__)),
        "source_class_counts": counts,
        "rows": rows,
        "pages": pages,
        "limitations": [
            "All rows were selected by the model's negative decision and reviewed after scoring by the same development agent.",
            "The 48-pixel crossing crops show source objects near tracked pixels; some are partly occluded.",
            "Stone-shaped pixels do not prove a distinct physical delivery, continuous same-stone identity, or a settled board.",
            "This review cannot estimate full-match throw-event precision or recall.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    print(counts)


if __name__ == "__main__":
    main()
