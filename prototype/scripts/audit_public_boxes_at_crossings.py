"""Test frozen public stone-box models exactly at selected passage pixels."""

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from stone_patch_detector import colour_proposals, detect_stones, load_model


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def distance(box, point):
    x, y, width, height = box
    return math.hypot(x + width / 2 - point[0], y + height / 2 - point[1])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--events", required=True, type=Path)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--model", action="append", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first probe")
    events, selected = (json.loads(path.read_text()) for path in (args.events, args.selection))
    source_hash = digest(args.video)
    if source_hash != events["source_sha256"] or source_hash != selected["source_sha256"]:
        parser.error("Source and input artifacts differ")
    event_rows = events.get("observed_events", events.get("events"))
    if event_rows is None:
        parser.error("Event file has no event list")
    by_id = {row["id"]: row for row in event_rows}
    if "new_review_candidates" in selected:
        choices = [
            (row["id"], row["candidate_time_s"], row["colour_claim"])
            for row in selected["new_review_candidates"]
        ]
    else:
        choices = [
            (row["candidate_id"], row["candidate_time_s"], row["colour_claim"])
            for row in selected["selected"]
        ]
    if any(event_id not in by_id for event_id, _, _ in choices):
        parser.error("Selection contains an unknown event ID")
    models = {path.parent.name: load_model(path) for path in args.model}
    if len(models) != len(args.model):
        parser.error("Model parent names must be unique")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened() or fps <= 0:
        parser.error("Unreadable video")
    rows = []
    for event_id, selected_time, selected_colour in choices:
        event = by_id[event_id]
        if event["crossing_time_s"] != selected_time or event["colour"] != selected_colour:
            raise ValueError(f"Selection content differs: {event_id}")
        point = [event["crossing_x_px"], event["passage_y_px"]]
        samples = []
        for offset in (-0.2, 0, 0.2):
            seconds = selected_time + offset
            cap.set(cv2.CAP_PROP_POS_FRAMES, round(seconds * fps))
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Could not decode {seconds:.3f}")
            _, proposals = colour_proposals(frame)
            near_proposals = [
                row
                for row in proposals
                if row["colour"] == selected_colour and distance(row["bbox"], point) <= 15
            ]
            results = {}
            for name, model in models.items():
                accepted = [
                    row
                    for row in detect_stones(frame, model)
                    if row["colour"] == selected_colour and distance(row["bbox"], point) <= 15
                ]
                results[name] = {
                    "accepted_near_crossing": bool(accepted),
                    "accepted_box_count": len(accepted),
                    "nearest_box_distance_px": min(
                        (distance(row["bbox"], point) for row in accepted), default=None
                    ),
                    "highest_accepted_score": max(
                        (row["confidence"] for row in accepted), default=None
                    ),
                }
            samples.append(
                {
                    "time_s": round(seconds, 3),
                    "raw_same_colour_proposals_within_15px": len(near_proposals),
                    "models": results,
                }
            )
        rows.append(
            {
                "event_id": event_id,
                "colour_claim": selected_colour,
                "crossing_time_s": selected_time,
                "crossing_point_px": point,
                "samples": samples,
                "accepted_samples_by_model": {
                    name: sum(
                        sample["models"][name]["accepted_near_crossing"] for sample in samples
                    )
                    for name in models
                },
            }
        )
    cap.release()
    output = {
        "status": "prediction_targeted_frozen_public_box_transfer_not_event_validation",
        "source_sha256": source_hash,
        "events_sha256": digest(args.events),
        "selection_sha256": digest(args.selection),
        "model_sha256": {path.parent.name: digest(path) for path in args.model},
        "runner_sha256": digest(Path(__file__)),
        "match_radius_px": 15,
        "sample_offsets_s": [-0.2, 0, 0.2],
        "cases": rows,
        "limitations": [
            "A nearby accepted box does not identify the delivered physical stone.",
            "Selected candidate windows are not an independent reference set.",
            "Missing boxes can arise from colour proposal failure, model score, occlusion or small source size.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "cases": len(rows),
                "detected_any": {
                    name: sum(row["accepted_samples_by_model"][name] > 0 for row in rows)
                    for name in models
                },
            }
        )
    )


if __name__ == "__main__":
    main()
