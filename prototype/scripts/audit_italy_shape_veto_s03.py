"""Source-check a Latvia-derived body veto on Italy raw candidate S03."""

from hashlib import sha256
import io
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "validation/source-cache/Vp3TIdOAlrc-360p.mp4"
EVENTS = (
    ROOT
    / "validation/throw-event-benchmark/layout-router/full-2024-coverage/new-preflight-italy24/run-02/events.json"
)
BOUNDARIES = (
    ROOT
    / "validation/throw-event-benchmark/canada-latvia-2024/crossing-shape-source-audit-development.json"
)
OUT = ROOT / "validation/throw-event-benchmark/canada-italy/shape-veto-s03-source-audit"
TIMES_S = (227.5, 227.9, 228.3, 228.7)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def source_frame(time_s):
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
    events = json.loads(EVENTS.read_text())
    audit = json.loads(BOUNDARIES.read_text())
    if digest(VIDEO) != events["source_sha256"]:
        raise ValueError("Italy source video differs from candidate run")
    if digest(EVENTS) != audit["cross_recording_proposal_distribution"]["italy24"]["input_sha256"]:
        raise ValueError("Italy candidate run differs from Latvia transfer audit")
    event = next(row for row in events["events"] if row["id"] == "S03")
    minimum_stone_body = audit["stone_preserving_in_sample_boundaries"][
        "minimum_stone_mean_body_support"
    ]
    if not event["mean_body_support"] < minimum_stone_body:
        raise ValueError("S03 is no longer flagged by the Latvia body threshold")
    if abs(event["crossing_time_s"] - TIMES_S[1]) > 0.1:
        raise ValueError("Saved source frames no longer bracket the S03 crossing")

    panels = []
    for time_s in TIMES_S:
        frame = source_frame(time_s)
        if frame.size != (640, 360):
            raise ValueError(f"Unexpected Italy frame size {frame.size}")
        left = frame.crop((0, 0, 320, 360))
        zoom = frame.crop((110, 20, 210, 120)).resize((320, 320), Image.Resampling.NEAREST)
        panel = Image.new("RGB", (320, 680), "white")
        panel.paste(left, (0, 0))
        panel.paste(zoom, (0, 360))
        draw = ImageDraw.Draw(panel)
        draw.rectangle((0, 0, 74, 20), fill="white")
        draw.text((4, 3), f"{time_s:.1f} s", fill="black")
        if time_s == TIMES_S[1]:
            x, y = event["crossing_x_px"], event["passage_y_px"]
            draw.ellipse((x - 12, y - 12, x + 12, y + 12), outline="red", width=2)
            zx, zy = (x - 110) * 3.2, 360 + (y - 20) * 3.2
            draw.ellipse((zx - 31, zy - 31, zx + 31, zy + 31), outline="red", width=3)
        panels.append(panel)
    sheet = Image.new("RGB", (1280, 680), "white")
    for index, panel in enumerate(panels):
        sheet.paste(panel, (index * 320, 0))
    OUT.mkdir(parents=True, exist_ok=True)
    image = OUT / "s03-source-sequence.jpg"
    sheet.save(image, quality=92)
    manifest = {
        "status": "same_agent_postproposal_source_pixel_review_not_throw_truth",
        "candidate_id": "S03",
        "source_id": events["source_id"],
        "source_video_sha256": digest(VIDEO),
        "raw_events_sha256": digest(EVENTS),
        "latvia_audit_sha256": digest(BOUNDARIES),
        "runner_sha256": digest(Path(__file__)),
        "source_frame_times_s": TIMES_S,
        "source_frame_size_px": [640, 360],
        "marked_crossing_pixel": [event["crossing_x_px"], event["passage_y_px"]],
        "source_pixel_class": "moving_stone_body_and_yellow_cap_pixels",
        "class_origin": "same_agent_postproposal_source_review",
        "physical_throw_verified": False,
        "mean_body_support": event["mean_body_support"],
        "latvia_stone_preserving_body_boundary": minimum_stone_body,
        "flagged_by_latvia_body_boundary": True,
        "image": image.name,
        "image_sha256": digest(image),
        "limitations": [
            "One prediction-selected Italy crossing; this is not a representative or independent sample.",
            "The frames show a moving stone-shaped object, not a verified release or full throw.",
            "The source review cannot estimate the full-match false-rejection rate.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    print(image.relative_to(ROOT))


if __name__ == "__main__":
    main()
