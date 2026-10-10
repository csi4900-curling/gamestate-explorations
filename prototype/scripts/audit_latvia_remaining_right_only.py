"""Preserve source-pixel review of the three unrepresented nonstone right-only paths."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
VIDEO = BASE / "source-360p.mp4"
SCAN = BASE / "full-right-area-first-transfer.json"
EPISODES = BASE / "full-right-area-episodes-first-transfer.json"
LEDGER = (
    BASE / "full-match-area-censored-candidate-handoff-two-area-gap-recoveries-development.json"
)
OUT = BASE / "remaining-right-only-source-audit"
CLASSES = {
    "A042": "broom_or_player_equipment_pixels",
    "A182": "person_jacket_logo_pixels",
    "A374": "person_clothing_or_wheelchair_pixels",
}


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Source audit already exists")
    scan = json.loads(SCAN.read_text())
    episodes = json.loads(EPISODES.read_text())
    ledger = json.loads(LEDGER.read_text())
    if (
        not scan["source_sha256"]
        == episodes["source_sha256"]
        == ledger["source_sha256"]
        == digest(VIDEO)
    ):
        raise ValueError("Source or right-inventory fingerprints differ")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened() or fps <= 0:
        raise ValueError("Source video unreadable")
    OUT.mkdir(parents=True)
    rows = []
    try:
        for track_id, pixel_class in CLASSES.items():
            proposals = [
                row
                for row in scan["directional_review_proposals"]
                if row["raw_track_id"] == track_id
            ]
            tracks = [row for row in scan["raw_tracks"] if row["track_id"] == track_id]
            episode_rows = [
                row
                for row in episodes["episodes"]
                if row["episode_kind"] == "right_only_candidate"
                and row["right_proposal_ids"] == ["R01:" + track_id]
            ]
            if len(proposals) != 1 or len(tracks) != 1 or len(episode_rows) != 1:
                raise ValueError(f"Right-only path is not unique: {track_id}")
            proposal, track, episode = proposals[0], tracks[0], episode_rows[0]
            if (
                proposal["passage"]["time_s"] != episode["observation_time_s"]
                or track["colour"] != proposal["colour_claim"]
            ):
                raise ValueError(f"Right-only proposal/episode differ: {track_id}")
            points = track["points"]
            indices = sorted(
                set((0, len(points) // 4, len(points) // 2, 3 * len(points) // 4, len(points) - 1))
            )
            selected = [points[i] for i in indices]
            panels = []
            for point in selected:
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(point["time_s"] * fps))
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise ValueError(f"Source frame unreadable: {track_id}")
                x, y, w, h = point["bbox"]
                cv2.rectangle(frame, (x - 5, y - 5), (x + w + 5, y + h + 5), (255, 0, 255), 2)
                cv2.putText(
                    frame,
                    f"{track_id} {point['time_s']:.0f}s",
                    (8, 24),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 0),
                    4,
                )
                cv2.putText(
                    frame,
                    f"{track_id} {point['time_s']:.0f}s",
                    (8, 24),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                )
                panels.append(frame)
            sheet = np.hstack(panels)
            image_path = OUT / f"{track_id}-source-frames.jpg"
            if not cv2.imwrite(str(image_path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 95]):
                raise ValueError(f"Cannot save source sheet: {track_id}")
            rows.append(
                {
                    "candidate_id": "right_area:R01:" + track_id,
                    "raw_track_id": track_id,
                    "episode_id": episode["episode_id"],
                    "source_time_s": proposal["passage"]["time_s"],
                    "time_semantics": proposal["passage_kind"],
                    "colour_claim": proposal["colour_claim"],
                    "direction": proposal["direction"],
                    "source_pixel_class": pixel_class,
                    "class_origin": "same_agent_postproposal_source_frame_review",
                    "observed_track_points": points,
                    "source_sheet": image_path.name,
                    "source_sheet_sha256": digest(image_path),
                    "source_frame_times_s": [point["time_s"] for point in selected],
                    "physical_throw_verified": False,
                }
            )
    finally:
        cap.release()
    result = {
        "status": "postproposal_three_remaining_right_only_nonstone_source_reviews_not_throw_truth",
        "source_video_sha256": digest(VIDEO),
        "right_area_scan_sha256": digest(SCAN),
        "episode_inventory_sha256": digest(EPISODES),
        "previous_ledger_sha256": digest(LEDGER),
        "runner_sha256": digest(Path(__file__)),
        "rows": rows,
        "limitations": [
            "Three paths were selected after reviewing the right-only inventory; labels are same-agent, not independent.",
            "The source class describes the tracked pixels, not all activity elsewhere in the source interval.",
            "These nonstone source paths do not establish that their surrounding intervals are throw-free.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"reviewed_nonstone_right_only": [row["candidate_id"] for row in rows]}))


if __name__ == "__main__":
    main()
