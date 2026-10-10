"""Render source pixels for all withheld Latvia left/right timing matches."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np


LEFT_CLASSES = {
    "S22": "person_jacket_logo", "S23": "person_face",
    "S76": "person_or_wheelchair_pixels",
    "S99": "ambiguous_low_red_pixels_near_wheelchair",
    "S100": "person_face", "S116": "person_face",
    "S117": "ambiguous_low_red_pixels_near_wheelchair",
    "S118": "person_head",
}
RIGHT_CLASSES = {
    "A046": "person_clothing", "A235": "person_clothing_or_wheelchair",
    "A332": "ambiguous_low_red_pixels_near_wheelchair",
    "A333": "ambiguous_low_red_pixels_near_wheelchair",
    "A483": "person_face",
}


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def card(frame, xy, label):
    x, y = (round(value) for value in xy)
    marked = frame.copy()
    cv2.circle(marked, (x, y), 10, (0, 255, 255), 2)
    x1, y1 = max(0, x - 28), max(0, y - 28)
    x2, y2 = min(640, x + 29), min(360, y + 29)
    crop = cv2.resize(marked[y1:y2, x1:x2], (456, 456),
                      interpolation=cv2.INTER_NEAREST)
    canvas = np.full((456, 1096, 3), 245, dtype=np.uint8)
    canvas[48:408, :640] = marked
    canvas[:, 640:] = crop
    cv2.putText(canvas, label, (12, 32), cv2.FONT_HERSHEY_SIMPLEX,
                0.75, (22, 31, 42), 2, cv2.LINE_AA)
    return canvas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("episodes", "raw-left", "right-probe", "video",
                 "output-dir"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    manifest_path = args.output_dir / "manifest.json"
    if manifest_path.exists():
        parser.error("Output exists")
    episodes, raw, right = (json.loads(path.read_text()) for path in
                            (args.episodes, args.raw_left, args.right_probe))
    source_hash = digest(args.video)
    if any(item["source_sha256"] != source_hash for item in
           (episodes, raw, right)):
        raise ValueError("Source video differs from candidate artifacts")
    matched = [row for row in episodes["episodes"] if
               row["right_proposal_ids"] and any(
                   status == "unconfirmed" for status in
                   row["left_screen_statuses"].values())]
    left_ids = {candidate_id for row in matched for candidate_id in
                row["member_left_candidate_ids"]}
    right_ids = {proposal_id.removeprefix("R01:") for row in matched for
                 proposal_id in row["right_proposal_ids"]}
    if (len(matched) != 4 or left_ids != set(LEFT_CLASSES) or
            right_ids != set(RIGHT_CLASSES)):
        raise ValueError("Withheld cross-view match inventory changed")
    withheld = {row["id"]: row for row in raw["withheld_events"]}
    proposals = {row["raw_track_id"]: row for row in
                 right["directional_review_proposals"]}
    if not left_ids <= set(withheld) or not right_ids <= set(proposals):
        raise ValueError("Matched source observations unavailable")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Could not open source video")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    try:
        for side, classes in (("left", LEFT_CLASSES), ("right", RIGHT_CLASSES)):
            for candidate_id, source_class in classes.items():
                if side == "left":
                    source = withheld[candidate_id]
                    time_s = source["crossing_time_s"]
                    xy = [source["crossing_x_px"], source["passage_y_px"]]
                else:
                    source = proposals[candidate_id]
                    time_s = source["passage"]["time_s"]
                    xy = source["passage"]["pixel"]
                cap.set(cv2.CAP_PROP_POS_MSEC, time_s * 1000)
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise ValueError(f"Cannot decode source at {time_s} s")
                image_path = args.output_dir / f"{candidate_id}.jpg"
                if image_path.exists() or not cv2.imwrite(str(image_path),
                    card(frame, xy, f"{candidate_id} / {side} / {time_s:.3f} s"),
                    [cv2.IMWRITE_JPEG_QUALITY, 92]):
                    raise ValueError(f"Could not safely write {image_path}")
                rows.append({
                    "candidate_id": candidate_id, "camera": side,
                    "source_time_s": time_s, "marked_source_pixel": xy,
                    "source_pixel_class": source_class,
                    "class_origin": "same_agent_postproposal_source_review",
                    "clearly_nonstone_at_marked_pixel": not
                        source_class.startswith("ambiguous_"),
                    "physical_throw_verified": False,
                    "image": image_path.name, "image_sha256": digest(image_path),
                })
    finally:
        cap.release()
    episode_rows = []
    for row in matched:
        episode_rows.append({
            "episode_id": row["episode_id"],
            "left_candidate_ids": row["member_left_candidate_ids"],
            "right_proposal_ids": row["right_proposal_ids"],
            "join_kind": row["episode_kind"],
            "source_review_result": (
                "clear_nonstone_paired_pixels" if row["episode_id"] in
                ("E023", "E078") else
                "person_pixels_and_occluded_low_red_pixels"),
            "promote_as_physical_throw": False,
        })
    output = {
        "status": "postproposal_same_agent_source_review_not_independent_event_truth",
        "source_video_sha256": source_hash,
        "input_sha256": {"episodes": digest(args.episodes),
                         "raw_left": digest(args.raw_left),
                         "right_probe": digest(args.right_probe)},
        "runner_sha256": digest(Path(__file__)),
        "matched_withheld_episode_count": len(episode_rows),
        "marked_left_count": len(LEFT_CLASSES),
        "marked_right_count": len(RIGHT_CLASSES),
        "marked_pixels": rows,
        "episodes": episode_rows,
        "limitations": [
            "The matched candidates were chosen after predictions were visible; source classes are not independent throw labels.",
            "Ambiguous low red pixels near wheelchairs cannot be identified as stones or physical deliveries from these stills.",
            "No dense review of every intervening frame was performed, so this does not establish that an episode contains no physical throw.",
            "Colour and timestamp agreement between cameras is insufficient to promote a withheld motion as a throw.",
        ],
    }
    manifest_path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"episodes": len(episode_rows),
                      "left": len(LEFT_CLASSES), "right": len(RIGHT_CLASSES)}))


if __name__ == "__main__":
    main()
