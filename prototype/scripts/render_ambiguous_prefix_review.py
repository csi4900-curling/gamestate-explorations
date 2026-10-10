"""Render source-only inspection sheets for ambiguous full-match motion paths."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
VIDEO = BASE / "source-1080p-full-format270.mp4"
MOTION = BASE / "full-match-motion-merged-postscore.json"
OUTPUT = BASE / "gap-review/ambiguous-prefix-review"


def digest(path):
    checksum = sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            checksum.update(block)
    return checksum.hexdigest()


def main():
    manifest_path = OUTPUT / "manifest.json"
    if manifest_path.exists():
        raise SystemExit("Ambiguous-prefix source review already exists")
    motion = json.loads(MOTION.read_text())
    source_hash = digest(VIDEO)
    if source_hash != motion["high_resolution_source_sha256"]:
        raise ValueError("Video does not match motion artifact")
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        raise RuntimeError(f"Cannot open {VIDEO}")
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    OUTPUT.mkdir(parents=True, exist_ok=True)
    try:
        for row in motion["rows"]:
            selection = row["selection"]
            if selection["status"] != "ambiguous_far_entry_motion_paths":
                continue
            prefix = selection["shared_prefix"]
            branches = selection["alternative_paths"]
            points_by_time = {}
            for node in prefix:
                points_by_time.setdefault(node["source_time_s"], []).append(
                    node["pixel_center"])
            for branch in branches:
                for node in branch:
                    points_by_time.setdefault(node["source_time_s"], []).append(
                        node["pixel_center"])
            times = sorted({prefix[0]["source_time_s"],
                            prefix[len(prefix) // 2]["source_time_s"],
                            prefix[-1]["source_time_s"],
                            selection["first_ambiguity_time_s"]})
            sheet = Image.new("RGB", (960 * 2, 600 * 2), "white")
            draw = ImageDraw.Draw(sheet)
            frames = []
            for i, time_s in enumerate(times):
                capture.set(cv2.CAP_PROP_POS_FRAMES,
                            round((time_s - motion["source_offset_s"]) * fps))
                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError(f"Cannot decode {row['candidate_id']} {time_s}")
                frame_index = int(capture.get(cv2.CAP_PROP_POS_FRAMES)) - 1
                annotated = frame[:, :960].copy() if row["receiving_view"] == "left" \
                    else frame[:, 960:].copy()
                centers = []
                for point in points_by_time[time_s]:
                    x, y = (round(v) for v in point)
                    if (x, y) in centers:
                        continue
                    centers.append((x, y))
                    local_x = x if row["receiving_view"] == "left" else x - 960
                    cv2.circle(annotated, (local_x, y), 28, (0, 255, 255), 4)
                x0, y0 = (i % 2) * 960, (i // 2) * 600
                scaled = cv2.resize(annotated, (960, 540),
                                    interpolation=cv2.INTER_AREA)
                sheet.paste(Image.fromarray(cv2.cvtColor(scaled, cv2.COLOR_BGR2RGB)),
                            (x0, y0 + 40))
                draw.text((x0 + 8, y0 + 9),
                          f"{row['candidate_id']} {row['colour']} {time_s:.1f}s frame {frame_index}",
                          fill="black")
                frames.append({"source_time_s": time_s,
                               "decoded_frame_index": frame_index,
                               "candidate_pixel_centers": centers})
            image = OUTPUT / f"{row['candidate_id'].lower()}-prefix.jpg"
            sheet.save(image, quality=92)
            rows.append({"candidate_id": row["candidate_id"],
                         "colour": row["colour"],
                         "receiving_view": row["receiving_view"],
                         "image": image.name,
                         "image_sha256": digest(image),
                         "prefix_sample_count": len(prefix),
                         "first_ambiguity_time_s": selection["first_ambiguity_time_s"],
                         "frames": frames})
    finally:
        capture.release()
    manifest_path.write_text(json.dumps({
        "status": "source_review_of_ambiguous_paths_not_independent_event_labels",
        "video_sha256": source_hash,
        "motion_sha256": digest(MOTION),
        "runner_sha256": digest(Path(__file__)),
        "candidate_count": len(rows),
        "rows": rows,
    }, indent=2) + "\n")
    print(len(rows), "review sheets", manifest_path)


if __name__ == "__main__":
    main()
