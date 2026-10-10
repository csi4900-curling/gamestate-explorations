"""Dense right lower-ice colour proposals during Latvia's blind displayed end 6.

This is a diagnostic for proposal coverage and motion direction, not a throw
detector. Small player/equipment patches can satisfy the colour mask.
"""

from collections import Counter
from hashlib import sha256
import json
from math import hypot
from pathlib import Path
import sys

import cv2


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from probe_static_left_right_cap_motion import right_colour_proposals

VIDEO = ROOT / "validation/throw-event-benchmark/canada-latvia-2024/source-360p.mp4"
SCAN = ROOT / "validation/throw-event-benchmark/canada-latvia-2024/end-marker-full-2d-local-development.json"
HANDOFF = ROOT / "validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1/full-match-candidate-partial-state-handoff.json"
OUT = ROOT / "validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1/end6-lower-cap-direction-development.json"
SAMPLE_PERIOD_S = 0.5
LOWER_Y_MIN = 235
MAX_GAP_S = 1.0
MAX_SPEED_PX_S = 80
MIN_SAMPLES = 3
MIN_VERTICAL_SPAN_PX = 20


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def link_lower_detections(samples):
    """Greedy image-local links; deliberately no persistent physical IDs."""
    tracks = []
    for sample in samples:
        time_s = sample["time_s"]
        for colour in ("red", "yellow"):
            points = sample["lower_colour_proposals"][colour]
            used = set()
            for track in tracks:
                if track["colour"] != colour:
                    continue
                last = track["points"][-1]
                gap = time_s-last["time_s"]
                if not 0 < gap <= MAX_GAP_S:
                    continue
                choices = [(hypot(point["pixel"][0]-last["pixel"][0],
                                  point["pixel"][1]-last["pixel"][1]), index)
                           for index, point in enumerate(points) if index not in used]
                if not choices:
                    continue
                distance, index = min(choices)
                if distance <= MAX_SPEED_PX_S * gap:
                    track["points"].append({"time_s": time_s, **points[index]})
                    used.add(index)
            for index, point in enumerate(points):
                if index not in used:
                    tracks.append({"colour": colour,
                                   "points": [{"time_s": time_s, **point}]})
    supported = []
    for track in tracks:
        points = track["points"]
        vertical = points[-1]["pixel"][1]-points[0]["pixel"][1]
        if len(points) < MIN_SAMPLES or abs(vertical) < MIN_VERTICAL_SPAN_PX:
            continue
        track["direction"] = "upward" if vertical < 0 else "downward"
        track["vertical_displacement_px"] = round(vertical, 2)
        track["first_observed_s"] = points[0]["time_s"]
        track["last_observed_s"] = points[-1]["time_s"]
        supported.append(track)
    supported.sort(key=lambda track: (track["first_observed_s"], track["colour"]))
    for index, track in enumerate(supported, 1):
        track["diagnostic_track_id"] = f"D{index:03d}"
    return supported


def main():
    if OUT.exists():
        raise SystemExit("Output exists; preserve previous diagnostic")
    scan = json.loads(SCAN.read_text())
    handoff = json.loads(HANDOFF.read_text())
    source_hash = digest(VIDEO)
    if source_hash != scan["video_sha256"] or source_hash != handoff["source_sha256"]:
        raise ValueError("Source provenance differs")
    end6 = [row for row in scan["samples"] if row["marker"] and
            row["marker"]["end"] == 6]
    if len(end6) < 2:
        raise ValueError("No repeated end-6 display")
    start = end6[0]["time_s"]
    blind = handoff["left_trigger_blind_intervals"]
    if len(blind) != 1 or not blind[0]["interval_s"][0] < start < blind[0]["interval_s"][1]:
        raise ValueError("Displayed end 6 and blind interval no longer overlap")
    stop = blind[0]["interval_s"][1]
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    samples = []
    for step in range(round((stop-start)/SAMPLE_PERIOD_S)+1):
        time_s = start+step*SAMPLE_PERIOD_S
        capture.set(cv2.CAP_PROP_POS_FRAMES, round(time_s*fps))
        ok, frame = capture.read()
        if not ok or frame.shape[:2] != (360, 640):
            raise RuntimeError(f"Could not decode {time_s}")
        all_proposals = right_colour_proposals(frame)
        lower = {colour: [row for row in all_proposals[colour]
                          if row["pixel"][1] >= LOWER_Y_MIN]
                 for colour in ("red", "yellow")}
        samples.append({"time_s": time_s,
                        "all_colour_proposal_count": {
                            colour: len(all_proposals[colour]) for colour in lower},
                        "lower_colour_proposals": lower})
    capture.release()
    tracks = link_lower_detections(samples)
    output = {
        "status": "dense_lower_right_colour_motion_not_stone_or_throw_truth",
        "source_sha256": source_hash,
        "marker_scan_sha256": digest(SCAN),
        "handoff_sha256": digest(HANDOFF),
        "colour_proposal_code_sha256": digest(ROOT / "prototype/scripts/probe_static_left_right_cap_motion.py"),
        "runner_sha256": digest(Path(__file__)),
        "interval_s": [start, stop],
        "sample_period_s": SAMPLE_PERIOD_S,
        "lower_y_min_px": LOWER_Y_MIN,
        "link_rule": {"max_gap_s": MAX_GAP_S,
                      "max_speed_px_per_s": MAX_SPEED_PX_S,
                      "min_samples": MIN_SAMPLES,
                      "min_absolute_vertical_displacement_px": MIN_VERTICAL_SPAN_PX},
        "sample_count": len(samples),
        "lower_proposal_count_by_colour": {
            colour: sum(len(row["lower_colour_proposals"][colour]) for row in samples)
            for colour in ("red", "yellow")},
        "supported_image_track_direction_counts": dict(Counter(
            (row["colour"], row["direction"]) for row in tracks)),
        "samples": samples,
        "image_motion_tracks": tracks,
        "limitations": [
            "Colour contours include people, equipment, handled stones and compression artefacts.",
            "Greedy nearest-neighbour links can switch objects and do not establish physical stone identity.",
            "A stone can be occluded or traverse between half-second samples.",
            "Motion direction is image-relative and cannot identify a delivery without source context.",
        ],
    }
    # JSON object keys must be strings rather than tuple-valued Counter keys.
    output["supported_image_track_direction_counts"] = {
        f"{colour}_{direction}": count
        for (colour, direction), count in Counter(
            (row["colour"], row["direction"]) for row in tracks).items()}
    OUT.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"interval_s": [start, stop],
                      "sample_count": len(samples),
                      "lower_proposal_count_by_colour": output[
                          "lower_proposal_count_by_colour"],
                      "direction_counts": output[
                          "supported_image_track_direction_counts"]}))


if __name__ == "__main__":
    main()
