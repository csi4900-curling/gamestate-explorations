"""Render exact source frames for the five lowest unreviewed patch scores."""

from hashlib import sha256
import io
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
VIDEO = BASE / "source-360p.mp4"
SCORE = BASE / "all-accepted-left-crossing-patch-score-development.json"
PACKET = BASE / "all-accepted-left-crossing-patch-packet/manifest.json"
OUT = BASE / "lowest-five-patch-source-audit"
EXPECTED_IDS = ("R01-S15", "R01-S05", "R01-S105", "R01-S13", "R01-S54")


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def frame_at(time_s):
    data = subprocess.check_output(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            str(time_s),
            "-i",
            str(VIDEO),
            "-frames:v",
            "1",
            "-f",
            "image2pipe",
            "-vcodec",
            "png",
            "-",
        ]
    )
    return Image.open(io.BytesIO(data)).convert("RGB")


def main():
    score = json.loads(SCORE.read_text())
    packet = json.loads(PACKET.read_text())
    source = packet["sources"]
    if (
        len(source) != 1
        or source[0]["video_sha256"] != digest(VIDEO)
        or not source[0]["same_video_bytes_as_timeline"]
        or score["packet_manifest_sha256"] != digest(PACKET)
    ):
        raise ValueError("Patch score, packet, and Latvia video lineage differ")
    selected = sorted(
        (row for row in score["rows"] if row["source_review"] == "unreviewed"),
        key=lambda row: (row["mean_score"], row["event_id"]),
    )[:5]
    if tuple(row["event_id"] for row in selected) != EXPECTED_IDS:
        raise ValueError("Lowest-score review selection changed")
    packet_by_id = {row["event_id"]: row for row in packet["rows"]}
    sheet = Image.new("RGB", (960, 380 * len(selected)), "white")
    rows = []
    for row_index, score_row in enumerate(selected):
        packet_row = packet_by_id[score_row["event_id"]]
        observations = []
        for sample_index, sample in enumerate(packet_row["samples"]):
            time_s = sample["time_s"]
            frame = frame_at(time_s)
            if frame.size != (640, 360):
                raise ValueError(f"Unexpected 360p source frame size {frame.size}")
            left = frame.crop((0, 0, 320, 360))
            x, y = sample["pixel"]
            draw = ImageDraw.Draw(left)
            draw.ellipse((x - 11, y - 11, x + 11, y + 11), outline="red", width=2)
            draw.rectangle((0, 0, 148, 20), fill="white")
            draw.text((4, 3), f"{score_row['event_id']} {time_s:.1f}", fill="black")
            sheet.paste(left, (sample_index * 320, row_index * 380))
            observations.append({"source_time_s": time_s, "marked_pixel": [x, y]})
        rows.append(
            {
                "candidate_id": score_row["event_id"],
                "frozen_patch_mean_score": score_row["mean_score"],
                "source_pixel_class": "yellow_cap_and_stone_body_pixels_on_path",
                "class_origin": "same_agent_postscore_source_review",
                "physical_throw_verified": False,
                "sampled_source_frames": observations,
            }
        )
    OUT.mkdir(parents=True, exist_ok=True)
    image = OUT / "lowest-five-source-frames.jpg"
    sheet.save(image, quality=90)
    manifest = {
        "status": "score_selected_postscore_source_pixel_review_not_event_truth",
        "source_video_sha256": digest(VIDEO),
        "score_sha256": digest(SCORE),
        "packet_manifest_sha256": digest(PACKET),
        "runner_sha256": digest(Path(__file__)),
        "selection": "five lowest mean scores among previously unreviewed accepted Latvia left crossings",
        "rows": rows,
        "image": image.name,
        "image_sha256": digest(image),
        "limitations": [
            "Selection was made after inspecting frozen model scores; this is not an unbiased sample.",
            "The three frames show stone-shaped pixels along each selected short path, not a verified full physical delivery.",
            "The result does not estimate full-match throw precision or recall.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    print(image.relative_to(ROOT))


if __name__ == "__main__":
    main()
