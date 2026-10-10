"""Measure stone-like cap motion in first-transfer non-origin candidates."""

from hashlib import sha256
import json
from math import ceil
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cap_patch_verifier import score_candidates
from short_cap_transit import short_transits
from stone_motion_fallback import stone_cap_candidates
from stone_patch_detector import load_model

BASE = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1"
MODEL = BASE / "model-excluding-swiss-transfer.npz"
OUTPUT = BASE / "nonorigin-cap-object-audit-development.json"
CASES = (
    ("norway", "S465", "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4", (6502.4, 6518.2)),
    ("swiss", "S171", "validation/throw-event-benchmark/paralympics-2022-sweden-switzerland/source.mp4", (2132.8, 2148.8)),
    ("swiss", "S322", "validation/throw-event-benchmark/paralympics-2022-sweden-switzerland/source.mp4", (3993.8, 4003.2)),
    ("swiss", "S404", "validation/throw-event-benchmark/paralympics-2022-sweden-switzerland/source.mp4", (5182.8, 5189.2)),
    ("swiss", "S566", "validation/throw-event-benchmark/paralympics-2022-sweden-switzerland/source.mp4", (7364.0, 7380.4)),
)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first audit")
    model = load_model(MODEL)
    inputs = {
        "norway": json.loads((BASE / "norway-end7-nonorigin-continuity-development.json").read_text()),
        "swiss": json.loads((BASE / "swiss-nonorigin-continuity-first.json").read_text()),
    }
    rows = []
    source_hashes = {}
    for source, shot_id, relative_video, interval in CASES:
        prior = next(row for row in inputs[source]["candidates"]
                     if row["shot_id"] == shot_id)
        if tuple(prior["interval_s"]) != interval:
            raise ValueError("Candidate window changed")
        video = ROOT / relative_video
        source_hash = source_hashes.setdefault(source, digest(video))
        if source_hash != inputs[source]["source_sha256"]:
            raise ValueError("Source mismatch")
        capture = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG,
                                   [cv2.CAP_PROP_N_THREADS, 1])
        fps = capture.get(cv2.CAP_PROP_FPS)
        step = round(fps / 5)
        first, last = (ceil(time_s * fps) for time_s in interval)
        capture.set(cv2.CAP_PROP_POS_FRAMES, first)
        observations = {colour: [] for colour in ("red", "yellow")}
        for frame_index in range(first, last):
            if not capture.grab():
                raise RuntimeError(f"Decode failed: {shot_id} {frame_index}")
            if frame_index % step:
                continue
            ok, frame = capture.retrieve()
            if not ok:
                raise RuntimeError(f"Retrieve failed: {shot_id} {frame_index}")
            t = round(frame_index / fps, 3)
            for colour in observations:
                raw = stone_cap_candidates(frame, colour,
                                           allow_bright_body=True,
                                           allow_large_caps=True)
                scored = score_candidates(frame, raw, model)
                observations[colour].append((t, [row for row in scored
                                                  if row["patch_score"] >= -0.6]))
        capture.release()
        evidence = {}
        for colour, stream in observations.items():
            transits = short_transits(stream)
            evidence[colour] = {
                "accepted_count": sum(len(items) for _, items in stream),
                "transits": transits,
                "accepted_samples": [{"time_s": t, "pixel": row["pixel"],
                                      "patch_score": round(row["patch_score"], 3)}
                                     for t, items in stream for row in items],
            }
        rows.append({"source": source, "shot_id": shot_id,
                     "interval_s": list(interval), "candidate_colour": prior["colour"],
                     "sample_rate_hz": fps / step, "evidence": evidence})
        print(source, shot_id, {colour: (data["accepted_count"],
               [(track["point_count"], track["displacement_px"],
                 track["median_patch_score"]) for track in data["transits"][:3]])
               for colour, data in evidence.items()}, flush=True)
    output = {
        "status": "postscore_source_only_cap_object_diagnostic_not_event_validation",
        "source_sha256": source_hashes,
        "input_sha256": {source: digest(BASE / (
            "norway-end7-nonorigin-continuity-development.json" if source == "norway"
            else "swiss-nonorigin-continuity-first.json")) for source in inputs},
        "model_sha256": digest(MODEL),
        "cap_verifier_code_sha256": digest(ROOT / "prototype/cap_patch_verifier.py"),
        "transit_code_sha256": digest(ROOT / "prototype/short_cap_transit.py"),
        "runner_sha256": digest(Path(__file__)),
        "rows": rows,
        "limitations": [
            "These cases were selected after inspecting source and counter failures.",
            "Stone-like patch motion is not proof of physical delivery or identity.",
            "No independent event labels enter this diagnostic.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")


if __name__ == "__main__":
    main()
