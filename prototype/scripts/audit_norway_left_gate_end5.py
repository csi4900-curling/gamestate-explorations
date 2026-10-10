"""Postscore left-facing gate diagnostic after the failed end-5 transfer."""

from collections import Counter
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

BASE = ROOT / "validation/curlobserver-learned-probe"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
ORIGINS = BASE / "canada-norway-full-transfer/shot-origin.json"
SHOTS = BASE / "canada-norway-full-transfer/cap-motion.json"
MODEL = BASE / "cap-patch-crossmatch-v1/model-excluding-swiss-transfer.npz"
FROZEN_GATE = BASE / "cap-patch-crossmatch-v1/norway-end4-departure-gate-development.json"
FROZEN_DECISION = BASE / "cap-patch-crossmatch-v1/norway-end4-departure-gate-events-development.json"
OUTPUT = BASE / "cap-patch-crossmatch-v1/norway-end5-left-gate-development.json"
X_LINE, Y_MIN, MIN_SCORE = 320, 280, -0.6
INTERVAL = (4187.0, 5206.5)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve the postscore left-gate scan")
    source_hash = digest(VIDEO)
    origin, shots = (json.loads(path.read_text()) for path in (ORIGINS, SHOTS))
    frozen_gate = json.loads(FROZEN_GATE.read_text())
    frozen_decision = json.loads(FROZEN_DECISION.read_text())
    if (origin["source_sha256"] != source_hash or shots["source_sha256"] != source_hash
            or frozen_gate["source_sha256"] != source_hash):
        raise ValueError("Source mismatch")
    if (frozen_gate["model_sha256"] != digest(MODEL) or
            frozen_decision["decision_code_sha256"] != digest(
                ROOT / "prototype/departure_gate_decision.py")):
        raise ValueError("Frozen cap model or decision rule changed")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash == reserved["source_sha256"]:
        raise ValueError("Reserved source is not development data")
    by_id = {row["shot_id"]: row for row in origin["rows"]}
    selected = [row for row in shots["shots"]
                if INTERVAL[0] <= sum(row["interval_s"]) / 2 < INTERVAL[1]
                and by_id[row["shot_id"]]["predicted"]]
    if len(selected) != 15 or selected[0]["shot_id"] != "S326" or selected[-1]["shot_id"] != "S373":
        raise ValueError("Predeclared end-5 origin selection changed")
    model = load_model(MODEL)
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    step = round(fps / 5)
    if fps <= 0 or step < 1:
        raise ValueError("Invalid source rate")
    rows = []
    for shot in selected:
        start, stop = shot["interval_s"]
        first, last = ceil(start * fps), ceil(stop * fps)
        capture.set(cv2.CAP_PROP_POS_FRAMES, first)
        observations = {colour: [] for colour in ("red", "yellow")}
        samples = []
        for frame_index in range(first, last):
            if not capture.grab():
                raise RuntimeError(f"Decode failed at frame {frame_index}")
            if frame_index % step:
                continue
            ok, frame = capture.retrieve()
            if not ok:
                raise RuntimeError(f"Retrieve failed at frame {frame_index}")
            t = round(frame_index / fps, 3)
            per_colour = {}
            for colour in observations:
                raw = stone_cap_candidates(frame, colour,
                                           allow_bright_body=True,
                                           allow_large_caps=True)
                scored = score_candidates(frame, raw, model)
                gated = [row for row in scored if row["pixel"][0] <= X_LINE
                         and row["pixel"][1] >= Y_MIN
                         and row["patch_score"] >= MIN_SCORE]
                observations[colour].append((t, gated))
                per_colour[colour] = gated
            samples.append({"time_s": t, "gate_candidates": per_colour})
        transits = {colour: short_transits(observations[colour])
                    for colour in observations}
        counts = Counter(colour for sample in samples for colour in observations
                         for _ in sample["gate_candidates"][colour])
        rows.append({"shot_id": shot["shot_id"], "interval_s": shot["interval_s"],
                     "sampled_frames": len(samples),
                     "gate_counts": {colour: counts[colour] for colour in observations},
                     "transits": transits, "samples": samples})
    capture.release()
    result = {
        "status": "postscore_end5_left_facing_early_ice_gate_diagnostic",
        "source_sha256": source_hash,
        "origin_sha256": digest(ORIGINS),
        "shot_manifest_sha256": digest(SHOTS),
        "frozen_end4_gate_sha256": digest(FROZEN_GATE),
        "frozen_end4_decision_sha256": digest(FROZEN_DECISION),
        "model_sha256": digest(MODEL),
        "gate_code_sha256": digest(Path(__file__)),
        "selection": "All 15 frozen origin-positive end-five shots, rescanned after the right-facing first transfer failed.",
        "selection_interval_s": list(INTERVAL),
        "gate": {"image_size": [640, 360], "x_max": X_LINE,
                 "y_min": Y_MIN, "minimum_patch_score": MIN_SCORE},
        "sample_rate_hz": fps / step,
        "rows": rows,
        "limitations": [
            "Left-facing geometry was selected after inspecting the failed end-five transfer and source frames.",
            "The pixel gate is specific to this Beijing delivery-side layout and cannot route other views automatically.",
            "A cap beyond the line is visual evidence, not a physical release or proven stone identity.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    for row in rows:
        print(row["shot_id"], row["gate_counts"],
              {colour: [(t["point_count"], t["displacement_px"])
                        for t in row["transits"][colour]]
               for colour in ("red", "yellow")})


if __name__ == "__main__":
    main()
