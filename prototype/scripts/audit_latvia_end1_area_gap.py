"""Preserve source evidence for right-area A008 omitted by the left-led handoff."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
VIDEO = BASE / "source-360p.mp4"
SCAN = BASE / "full-right-area-first-transfer.json"
LEDGER = BASE / "full-match-area-censored-candidate-handoff-end5-gap-development.json"
OUT = BASE / "end1-omitted-right-area-source-audit"


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
    ledger = json.loads(LEDGER.read_text())
    if scan["source_sha256"] != ledger["source_sha256"] != digest(VIDEO):
        raise ValueError("Right scan, ledger, and source video differ")
    proposals = [
        row for row in scan["directional_review_proposals"] if row["raw_track_id"] == "A008"
    ]
    tracks = [row for row in scan["raw_tracks"] if row["track_id"] == "A008"]
    if len(proposals) != 1 or len(tracks) != 1:
        raise ValueError("A008 is not a unique right-area source proposal")
    proposal, track = proposals[0], tracks[0]
    points = track["points"]
    time_s = proposal["passage"]["time_s"]
    if (
        not proposal["colour_claim"] == track["colour"] == "red"
        or proposal["direction"] != "negative_y"
        or len(points) != 6
        or [row["time_s"] for row in points] != [347.0, 348.0, 349.0, 350.0, 351.0, 352.0]
        or not 348 <= time_s <= 350
    ):
        raise ValueError("A008 source path differs from inspected inventory")
    existing = [
        row
        for row in ledger["ordered_candidates"]
        if row["observation_kind"] != "left_unconfirmed_raw_motion"
        and abs(row["source_time_s"] - time_s) <= 15
    ]
    if existing or any(
        row["candidate_id"] == "right_area:R01:A008" for row in ledger["ordered_candidates"]
    ):
        raise ValueError("A008 overlaps an existing possible-event proposal")
    prior = max(
        (
            row
            for row in ledger["ordered_candidates"]
            if row["source_time_s"] < time_s
            and row["observation_kind"] != "left_unconfirmed_raw_motion"
        ),
        key=lambda row: row["source_time_s"],
    )
    following = min(
        (
            row
            for row in ledger["ordered_candidates"]
            if row["source_time_s"] > time_s
            and row["observation_kind"] != "left_unconfirmed_raw_motion"
        ),
        key=lambda row: row["source_time_s"],
    )
    if (
        prior["candidate_id"] != "left:R01-S07"
        or following["candidate_id"] != "left:R01-S11"
        or prior["colour_claim"] != following["colour_claim"] != "yellow"
    ):
        raise ValueError("Adjacent review sequence differs")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened() or fps <= 0:
        raise ValueError("Source video unreadable")
    frames = []
    try:
        for point in points:
            cap.set(cv2.CAP_PROP_POS_FRAMES, round(point["time_s"] * fps))
            ok, frame = cap.read()
            if not ok or frame.shape[:2] != (360, 640):
                raise ValueError("A008 source frame unreadable")
            x, y, w, h = point["bbox"]
            cv2.rectangle(frame, (x - 5, y - 5), (x + w + 5, y + h + 5), (255, 0, 255), 2)
            cv2.putText(
                frame,
                f"A008 {point['time_s']:.0f}s",
                (8, 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 0),
                4,
            )
            cv2.putText(
                frame,
                f"A008 {point['time_s']:.0f}s",
                (8, 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )
            frames.append(frame)
    finally:
        cap.release()
    OUT.mkdir(parents=True)
    sheet = np.vstack((np.hstack(frames[:3]), np.hstack(frames[3:])))
    image_path = OUT / "A008-source-frames.jpg"
    if not cv2.imwrite(str(image_path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 95]):
        raise ValueError("Could not save A008 source sheet")
    result = {
        "status": "postproposal_same_agent_source_pixel_review_not_physical_throw_truth",
        "source_video_sha256": digest(VIDEO),
        "right_area_scan_sha256": digest(SCAN),
        "previous_ledger_sha256": digest(LEDGER),
        "runner_sha256": digest(Path(__file__)),
        "source_sheet": image_path.name,
        "source_sheet_sha256": digest(image_path),
        "raw_track_id": "A008",
        "candidate_id": "right_area:R01:A008",
        "source_time_s": time_s,
        "time_semantics": proposal["passage_kind"],
        "colour_claim": "red",
        "direction": "negative_y",
        "source_pixel_class": "moving_red_stone_body_pixels",
        "class_origin": "same_agent_postproposal_six_frame_source_review",
        "observed_track_points": points,
        "prior_proposal": {
            "candidate_id": prior["candidate_id"],
            "source_time_s": prior["source_time_s"],
            "colour_claim": prior["colour_claim"],
        },
        "following_proposal": {
            "candidate_id": following["candidate_id"],
            "source_time_s": following["source_time_s"],
            "colour_claim": following["colour_claim"],
        },
        "physical_throw_verified": False,
        "same_stone_identity_to_board_verified": False,
        "limitations": [
            "The review was targeted after observing an end-one candidate gap and is not independent throw truth.",
            "Six source frames show moving red stone pixels, not the entire delivery or settle.",
            "A right-camera image path does not establish a complete metric trajectory or board state.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "candidate_id": result["candidate_id"],
                "time_s": result["source_time_s"],
                "source_pixel_class": result["source_pixel_class"],
            }
        )
    )


if __name__ == "__main__":
    main()
