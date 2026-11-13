"""Compare the departure event colour with the receiving stone colour at handoff.

This is a post-hoc identity diagnostic, not a re-identification model. It reads
the first receiving observation of each linked segment, finds the matching board
detection at that source sample, crops it, and applies the same OpenCLIP
red/yellow ranking used for event colours. Agreement is supporting evidence;
disagreement is positive evidence that the link (or the classifier) is wrong.
Same-colour stones remain indistinguishable.
"""

import argparse
import hashlib
import json
import time
from collections import Counter
from pathlib import Path

import cv2


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def panel_of(camera):
    return "left" if str(camera).startswith("left") else "right"


def collect_needed(aggregate, event_colours):
    colour_by_event = {row["event_id"]: row for row in event_colours.get("events", [])}
    needed = {}
    for event in aggregate.get("events", []):
        colour = colour_by_event.get(event["candidate_id"])
        if not colour or colour.get("colour") is None:
            continue
        for link in event.get("cross_view_links", []):
            receiving = next((s for s in event["segments"]
                              if s["segment_id"] == link["receiving_segment"]), None)
            if receiving is None or not receiving.get("pixel_points"):
                continue
            first = receiving["pixel_points"][0]
            key = round(float(first["time_s"]), 1)
            needed.setdefault(key, []).append({
                "event_id": event["candidate_id"],
                "link": link,
                "segment_id": receiving["segment_id"],
                "camera": receiving.get("camera"),
                "panel": panel_of(receiving.get("camera")),
                "tracker_id": receiving.get("tracker_id"),
                "time_s": float(first["time_s"]),
                "pixel": first["pixel"],
                "departure_colour": colour.get("colour"),
                "departure_colour_status": colour.get("colour_status"),
            })
    return needed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--aggregate", type=Path, required=True)
    parser.add_argument("--match-observations", type=Path, required=True)
    parser.add_argument("--event-colours", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Output exists; preserve the previous run")
    from prototype.stone_colour_model import StoneColourModel
    aggregate = json.loads(args.aggregate.read_text())
    event_colours = json.loads(args.event_colours.read_text())
    needed = collect_needed(aggregate, event_colours)
    if not needed:
        raise SystemExit("No linked receiving observations with an event colour")
    # One pass over the board stream for the required sample times.
    board_rows = {}
    with args.match_observations.open() as stream:
        for line in stream:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = round(float(row["time_s"]), 1)
            if key in needed and key not in board_rows:
                board_rows[key] = row
    model = StoneColourModel(args.config)
    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise SystemExit("Cannot open source video")
    started = time.perf_counter()
    rows = []
    try:
        for key, items in sorted(needed.items()):
            board = board_rows.get(key)
            for item in items:
                if board is None:
                    rows.append({**item, "status": "no_board_row",
                                 "receiving_colour": None})
                    continue
                panel_stones = ((board.get("boards") or {}).get(item["panel"])
                                or {}).get("stones") or []
                match = next((s for s in panel_stones
                              if s.get("tracker_id") == item["tracker_id"]), None)
                if match is None:
                    rows.append({**item, "status": "no_tracker_id_match",
                                 "receiving_colour": None})
                    continue
                matched_by = "tracker_id"
                bbox = match.get("bbox_xyxy")
                if not bbox:
                    rows.append({**item, "status": "no_bbox",
                                 "receiving_colour": None})
                    continue
                frame_index = int(board["frame_index"])
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                ok, frame = cap.read()
                actual = round(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
                if not ok or actual != frame_index:
                    rows.append({**item, "status": "decode_failed",
                                 "receiving_colour": None})
                    continue
                try:
                    result = model.classify(frame, [{"bbox_xyxy": bbox}])[0]
                except (ValueError, RuntimeError) as exc:
                    rows.append({**item, "status": "classify_failed",
                                 "reason": f"{type(exc).__name__}: {exc}",
                                 "receiving_colour": None})
                    continue
                receiving_colour = result.get("prediction")
                if receiving_colour is None:
                    status = "receiving_unavailable"
                elif receiving_colour == item["departure_colour"]:
                    status = "agree"
                else:
                    status = "disagree"
                rows.append({
                    **item,
                    "status": status,
                    "matched_by": matched_by,
                    "board_tracker_id": match.get("tracker_id"),
                    "bbox_xyxy": bbox,
                    "frame_index": frame_index,
                    "receiving_colour": receiving_colour,
                    "receiving_cosine_similarity": result.get("cosine_similarity"),
                    "receiving_colour_status": result.get("status"),
                    "calibrated_confidence": False,
                    "physical_identity_verified": False,
                    "same_colour_ambiguity_remaining": True,
                })
    finally:
        cap.release()
    counts = Counter(row["status"] for row in rows)
    verified = counts["agree"] + counts["disagree"]
    result = {
        "schema_version": "handoff-colour-diagnostic-v1",
        "aggregate_sha256": digest(args.aggregate),
        "match_observations_sha256": digest(args.match_observations),
        "event_colours_sha256": digest(args.event_colours),
        "source_sha256": digest(args.video),
        "handoffs": rows,
        "summary": {
            "handoffs": len(rows),
            "agree": counts["agree"],
            "disagree": counts["disagree"],
            "unverified": len(rows) - verified,
            "colour_consistency_among_verified": (
                counts["agree"] / verified if verified else None),
            "wall_seconds": time.perf_counter() - started,
            "physical_identity_verified": False,
            "same_colour_ambiguity_remaining": True,
        },
        "provenance": {
            "model": model.provenance,
            "method": "departure event colour vs matched receiving board-stone crop",
            "limitations": [
                "Forced-choice red/yellow ranking; errors are possible.",
                "Receiving crop may contain other stones or occluders.",
                "Agreement supports but does not prove a handoff; disagreement may be a classifier or link error.",
                "Same-colour stones remain indistinguishable.",
            ],
        },
    }
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result["summary"]))


if __name__ == "__main__":
    main()
