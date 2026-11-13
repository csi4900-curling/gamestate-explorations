"""Post-hoc OpenCLIP colour evidence for learned event detections.

The frozen event/dense run does not classify colour. This pass crops the two
observed detector boxes around each configured-line crossing and ranks red vs
yellow with the existing upstream OpenCLIP component. It does not change the
frozen run, does not map colour to team, and does not establish physical
identity. Agreements, disagreements and abstentions are all reported.
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


def classify_event(model, cap, event, fps):
    rows = []
    for observation in event.get("observations", []):
        frame_index = round(observation["time_s"] * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = cap.read()
        actual = round(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
        if not ok or actual != frame_index:
            rows.append({"time_s": observation["time_s"],
                         "frame_index": frame_index,
                         "status": "decode_failed",
                         "prediction": None})
            continue
        try:
            result = model.classify(frame, [{"bbox_xyxy": observation["bbox_xyxy"]}])[0]
        except (ValueError, RuntimeError) as exc:
            rows.append({"time_s": observation["time_s"],
                         "frame_index": frame_index,
                         "status": "classify_failed",
                         "reason": f"{type(exc).__name__}: {exc}",
                         "prediction": None})
            continue
        rows.append({
            "time_s": observation["time_s"],
            "frame_index": frame_index,
            "bbox_xyxy": observation["bbox_xyxy"],
            "status": result.get("status"),
            "prediction": result.get("prediction"),
            "cosine_similarity": result.get("cosine_similarity"),
            "calibrated_confidence": False,
            "team": None,
        })
    predictions = [row for row in rows
                   if row.get("status") == "unverified_colour_ranking"]
    colours = {row["prediction"] for row in predictions}
    if len(predictions) >= 2 and len(colours) == 1:
        colour, status = next(iter(colours)), "two_observation_agreement"
    elif len(predictions) == 1:
        colour, status = predictions[0]["prediction"], "single_observation"
    elif len(colours) > 1:
        colour, status = None, "observation_disagreement"
    else:
        colour, status = None, "unavailable"
    return {
        "event_id": event["id"],
        "crossing_time_s": event["crossing_time_s"],
        "track_id": event.get("track_id"),
        "colour": colour,
        "colour_status": status,
        "observations": rows,
        "team": None,
        "physical_identity_verified": False,
    }


def reference_comparison(events, reference_path, max_cost=2.0):
    references = json.loads(Path(reference_path).read_text()).get("events") or []
    pairs = []
    for ri, ref in enumerate(references):
        lo, hi = ref["delivery_interval_s"]
        for ei, event in enumerate(events):
            t = event["crossing_time_s"]
            cost = 0.0 if lo <= t <= hi else min(abs(t - lo), abs(t - hi))
            if cost <= max_cost:
                pairs.append((cost, ri, ei))
    pairs.sort()
    used_ref, used_event, comparisons = set(), set(), []
    for cost, ri, ei in pairs:
        if ri in used_ref or ei in used_event:
            continue
        used_ref.add(ri)
        used_event.add(ei)
        ref = references[ri]
        event = events[ei]
        predicted, expected = event.get("colour"), ref.get("colour")
        status = ("correct" if predicted == expected and predicted is not None
                  else "incorrect" if predicted is not None
                  else "abstained")
        comparisons.append({"reference_id": ref["id"],
                            "event_id": event["event_id"],
                            "reference_colour": expected,
                            "predicted_colour": predicted,
                            "status": status})
    counts = Counter(row["status"] for row in comparisons)
    return {
        "reference": str(reference_path),
        "matched": len(comparisons),
        "correct": counts["correct"],
        "incorrect": counts["incorrect"],
        "abstained": counts["abstained"],
        "accuracy_among_answered": (
            counts["correct"] / (counts["correct"] + counts["incorrect"])
            if counts["correct"] + counts["incorrect"] else None),
        "answer_coverage": (
            (counts["correct"] + counts["incorrect"]) / len(comparisons)
            if comparisons else None),
        "comparisons": comparisons,
        "independent_ground_truth": False,
        "scope": "Assistant-labelled reference colours; development only.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--references", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Output exists; preserve the previous run")
    from prototype.stone_colour_model import StoneColourModel
    events_doc = json.loads(args.events.read_text())
    fps = float(events_doc["source_fps"])
    model = StoneColourModel(args.config)
    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise SystemExit("Cannot open source video")
    started = time.perf_counter()
    rows = []
    try:
        for event in events_doc["events"]:
            rows.append(classify_event(model, cap, event, fps))
    finally:
        cap.release()
    summary = {
        "events": len(rows),
        "two_observation_agreement": sum(
            1 for row in rows if row["colour_status"] == "two_observation_agreement"),
        "single_observation": sum(
            1 for row in rows if row["colour_status"] == "single_observation"),
        "disagreement": sum(
            1 for row in rows if row["colour_status"] == "observation_disagreement"),
        "unavailable": sum(
            1 for row in rows if row["colour_status"] == "unavailable"),
        "red": sum(1 for row in rows if row["colour"] == "red"),
        "yellow": sum(1 for row in rows if row["colour"] == "yellow"),
        "wall_seconds": time.perf_counter() - started,
        "calibrated_confidence": False,
        "team_mapping_established": False,
        "physical_identity_verified": False,
    }
    result = {
        "schema_version": "event-colour-development-v1",
        "source_sha256": digest(args.video),
        "events_sha256": digest(args.events),
        "events": rows,
        "summary": summary,
        "provenance": {
            "model": model.provenance,
            "config": str(args.config.resolve()),
            "config_sha256": digest(args.config),
            "source_video": str(args.video.resolve()),
            "event_detections": str(args.events.resolve()),
            "method": "OpenCLIP forced-choice red/yellow prompts on detector crops",
            "limitations": [
                "Forced choice among two prompts; non-stone or mixed crops can be wrong.",
                "No calibrated confidence; no team mapping.",
                "Colour is not a physical stone identity.",
                "Two observations per event are not independent stones.",
            ],
        },
    }
    if args.references:
        result["reference_comparison"] = reference_comparison(rows, args.references)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result["summary"]))


if __name__ == "__main__":
    main()
