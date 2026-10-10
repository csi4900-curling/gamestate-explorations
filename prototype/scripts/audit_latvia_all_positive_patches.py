"""Preserve source-pixel reviews of every frozen-positive accepted Latvia crossing."""

import json
from pathlib import Path

from PIL import Image, ImageDraw

import audit_latvia_all_negative_patches as common


ROOT, BASE = common.ROOT, common.BASE
SCORE, PACKET, VIDEO = common.SCORE, common.PACKET, common.VIDEO
OUT = BASE / "all-positive-patch-source-audit"
POSITIVE_IDS = (
    "R01-S32", "R01-S81", "R01-S39", "R01-S90", "R01-S87", "R01-S40",
    "R01-S89", "R01-S07", "R01-S95", "R01-S94", "R01-S91", "R01-S28",
    "R01-S82", "R01-S34", "R01-S83", "R01-S88", "R01-S97", "R01-S96",
    "R01-S38", "R01-S33", "R01-S42", "R01-S29", "R01-S18", "R01-S59",
    "R01-S26", "R01-S63", "R01-S04", "R01-S67", "R01-S112", "R01-S70",
    "R01-S107", "R01-S56", "R01-S65", "R01-S110", "R01-S104", "R01-S20",
    "R01-S114", "R01-S06",
)


def main():
    score = json.loads(SCORE.read_text())
    packet = json.loads(PACKET.read_text())
    if (score["packet_manifest_sha256"] != common.digest(PACKET) or
            len(packet["sources"]) != 1 or
            packet["sources"][0]["video_sha256"] != common.digest(VIDEO) or
            not packet["sources"][0]["same_video_bytes_as_timeline"]):
        raise ValueError("Score, packet, and Latvia source fingerprints differ")
    positives = sorted((row for row in score["rows"] if row["predicted_stone_like"]),
                       key=lambda row: (row["mean_score"], row["event_id"]))
    if tuple(row["event_id"] for row in positives) != POSITIVE_IDS:
        raise ValueError("Frozen positive crossing inventory changed")
    by_id = {row["event_id"]: row for row in packet["rows"]}
    OUT.mkdir(parents=True, exist_ok=True)
    rows, pages = [], []
    for page_index in range(5):
        chunk = positives[page_index * 9:(page_index + 1) * 9]
        sheet = Image.new("RGB", (576, 192 * len(chunk)), "white")
        draw = ImageDraw.Draw(sheet)
        for local_index, score_row in enumerate(chunk):
            event_id = score_row["event_id"]
            crop_hashes = []
            for sample_index, sample in enumerate(by_id[event_id]["samples"]):
                crop = BASE / "all-accepted-left-crossing-patch-packet" / sample["crop_path"]
                if common.digest(crop) != sample["crop_sha256"]:
                    raise ValueError(f"Crop hash mismatch: {crop}")
                image = Image.open(crop).convert("RGB")
                if image.size != (48, 48):
                    raise ValueError(f"Unexpected crop geometry: {crop}")
                sheet.paste(image.resize((192, 192), Image.Resampling.NEAREST),
                            (sample_index * 192, local_index * 192))
                crop_hashes.append(sample["crop_sha256"])
            y = local_index * 192
            draw.rectangle((0, y, 132, y + 20), fill="white")
            draw.text((3, y + 3), f"{event_id} {score_row['mean_score']:.2f}", fill="red")
            rows.append({
                "candidate_id": event_id,
                "frozen_patch_mean_score": score_row["mean_score"],
                "source_pixel_class": "stone_body_pixels_in_crossing_crops",
                "class_origin": "same_agent_postscore_crossing_crop_review",
                "physical_throw_verified": False,
                "review_page": f"positive-page-{page_index + 1}.jpg",
                "crop_sha256": crop_hashes,
            })
        page = OUT / f"positive-page-{page_index + 1}.jpg"
        sheet.save(page, quality=90)
        pages.append({"image": page.name, "sha256": common.digest(page),
                      "candidate_count": len(chunk)})
    if len(rows) != 38:
        raise ValueError("Positive source review count changed")
    manifest = {
        "status": "postscore_all_positive_source_pixel_review_not_throw_truth",
        "selection": "all 38 frozen-model-positive accepted left crossings",
        "source_video_sha256": common.digest(VIDEO),
        "score_sha256": common.digest(SCORE),
        "packet_manifest_sha256": common.digest(PACKET),
        "runner_sha256": common.digest(Path(__file__)),
        "helper_code_sha256": common.digest(Path(common.__file__)),
        "source_class_counts": {"stone_body_pixels_in_crossing_crops": len(rows)},
        "rows": rows,
        "pages": pages,
        "limitations": [
            "All rows were selected by the model's positive decision and reviewed after scoring by the same development agent.",
            "The 48-pixel crossing crops show stone bodies near tracked pixels; they do not establish physical deliveries.",
            "The result does not estimate complete-match throw precision, recall, or F1.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    print(manifest["source_class_counts"])


if __name__ == "__main__":
    main()
