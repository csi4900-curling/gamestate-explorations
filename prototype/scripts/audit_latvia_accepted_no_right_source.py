"""Render all accepted Latvia left passages without a right-time candidate."""

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def frame_at(video, source_time_s):
    result = subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-ss",
        str(source_time_s), "-i", str(video), "-frames:v", "1", "-f",
        "image2pipe", "-vcodec", "png", "-"],
        check=True, capture_output=True)
    frame = Image.open(BytesIO(result.stdout)).convert("RGB")
    if frame.size != (640, 360):
        raise ValueError("Unexpected source-frame size")
    return frame


def card(frame, xy, label):
    x, y = (round(value) for value in xy)
    marked = frame.copy()
    draw = ImageDraw.Draw(marked)
    draw.ellipse((x-10, y-10, x+10, y+10), outline="yellow", width=2)
    crop = marked.crop((max(0, x-28), max(0, y-28),
                        min(640, x+29), min(360, y+29)))
    crop = crop.resize((456, 456), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (1096, 456), (245, 245, 245))
    canvas.paste(marked, (0, 48))
    canvas.paste(crop, (640, 0))
    ImageDraw.Draw(canvas).text((12, 15), label, fill=(22, 31, 42))
    return canvas


PIXEL_CLASSES = {
    "S04": "stone_body_and_red_cap_pixels",
    "S45": "person_head_pixels",
    "S49": "stone_body_and_red_cap_pixels",
    "S59": "stone_body_and_red_cap_pixels",
    "S67": "stone_body_and_red_cap_pixels",
    "S90": "stone_body_and_red_cap_pixels",
    "S104": "stone_body_and_red_cap_pixels",
    "S110": "stone_body_and_red_cap_pixels",
    "S114": "stone_body_and_red_cap_pixels",
    "S119": "ambiguous_yellow_pixels_near_player",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("episodes", "raw-left", "video", "output-dir"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    manifest_path = args.output_dir / "manifest.json"
    if manifest_path.exists():
        parser.error("Output exists")
    episodes = json.loads(args.episodes.read_text())
    raw = json.loads(args.raw_left.read_text())
    source_hash = digest(args.video)
    if (episodes["source_sha256"] != source_hash or
            raw["source_sha256"] != source_hash):
        raise ValueError("Source fingerprint differs")
    accepted = {row["id"]: row for row in raw["events"]}
    unmatched = [row for row in episodes["left_joins"] if
                 row["left_candidate_id"] in accepted and
                 row["corroboration_tier"] ==
                 "no_right_time_colour_direction_candidate"]
    if {row["left_candidate_id"] for row in unmatched} != set(PIXEL_CLASSES):
        raise ValueError("Accepted no-right inventory changed")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for join in unmatched:
        candidate_id = join["left_candidate_id"]
        event = accepted[candidate_id]
        time_s = event["crossing_time_s"]
        xy = [event["crossing_x_px"], event["passage_y_px"]]
        if (time_s != join["left_passage_time_s"] or
                event["colour"] != join["colour_claim"]):
            raise ValueError("Left event differs from episode join")
        frame = frame_at(args.video, time_s)
        image_path = args.output_dir / f"{candidate_id}.jpg"
        if image_path.exists():
            raise ValueError(f"Output exists: {image_path}")
        card(frame, xy, f"{candidate_id} / left / {time_s:.3f} s").save(
            image_path, quality=92)
        pixel_class = PIXEL_CLASSES[candidate_id]
        rows.append({
                "left_candidate_id": candidate_id,
                "source_time_s": time_s,
                "colour_claim": event["colour"],
                "marked_source_pixel": xy,
                "source_pixel_class": pixel_class,
                "stone_shaped_pixels_at_crossing": (
                    True if pixel_class.startswith("stone_body") else
                    False if pixel_class.startswith("person_") else None),
                "right_time_colour_direction_candidate_count": 0,
                "class_origin": "same_agent_postproposal_source_review",
                "physical_throw_verified": False,
                "image": image_path.name,
                "image_sha256": digest(image_path),
            })
    output = {
        "status": "postproposal_accepted_left_no_right_source_review_not_throw_truth",
        "source_video_sha256": source_hash,
        "input_sha256": {"episodes": digest(args.episodes),
                         "raw_left": digest(args.raw_left)},
        "runner_sha256": digest(Path(__file__)),
        "frame_decoder": "ffmpeg_image2pipe_png",
        "accepted_left_without_right_count": len(rows),
        "stone_shaped_pixel_count": sum(row[
            "stone_shaped_pixels_at_crossing"] is True for row in rows),
        "clearly_person_pixel_count": sum(row[
            "stone_shaped_pixels_at_crossing"] is False for row in rows),
        "ambiguous_pixel_count": sum(row[
            "stone_shaped_pixels_at_crossing"] is None for row in rows),
        "rows": rows,
        "limitations": [
            "The review was selected after seeing accepted predictions and missing right links; it is not independent event truth.",
            "One marked frame establishes local stone-shaped pixels, not continuous same-stone identity or physical delivery.",
            "No compatible right proposal does not prove the stone was absent from the right source image.",
            "Accepted event precision, full-match recall and F1 remain unmeasured.",
        ],
    }
    manifest_path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"accepted_no_right": len(rows),
                      "stone_pixels": output["stone_shaped_pixel_count"],
                      "person_pixels": output["clearly_person_pixel_count"],
                      "ambiguous": output["ambiguous_pixel_count"]}))


if __name__ == "__main__":
    main()
