"""First source-only end-7 scan of frozen mirrored early-ice gate cues."""

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
STUDY = BASE / "cap-patch-crossmatch-v1"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
ORIGINS = BASE / "canada-norway-full-transfer/shot-origin.json"
SHOTS = BASE / "canada-norway-full-transfer/cap-motion.json"
MODEL = STUDY / "model-excluding-swiss-transfer.npz"
FROZEN_RIGHT = STUDY / "norway-end4-departure-gate-development.json"
FROZEN_LEFT = STUDY / "norway-end5-left-gate-development.json"
FROZEN_ROUTER = STUDY / "norway-end4-end5-dual-gate-development.json"
OUTPUT = STUDY / "norway-end7-dual-gate-first.json"
INTERVAL = (6364.3, 7372.1)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first end-7 dual-gate scan")
    source_hash = digest(VIDEO)
    origins, shots = (json.loads(path.read_text()) for path in (ORIGINS, SHOTS))
    right, left, router = (
        json.loads(path.read_text()) for path in (FROZEN_RIGHT, FROZEN_LEFT, FROZEN_ROUTER)
    )
    if any(row["source_sha256"] != source_hash for row in (origins, shots, right, left, router)):
        raise ValueError("Source mismatch")
    if (
        right["model_sha256"] != digest(MODEL)
        or left["model_sha256"] != digest(MODEL)
        or router["router_code_sha256"] != digest(ROOT / "prototype/dual_departure_gate.py")
        or router["colour_code_sha256"] != digest(ROOT / "prototype/departure_gate_decision.py")
    ):
        raise ValueError("Frozen model, router or colour rule changed")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash == reserved["source_sha256"]:
        raise ValueError("Reserved independent source is not development data")
    gates = {"left": left["gate"], "right": right["gate"]}
    if gates != {
        "left": {"image_size": [640, 360], "x_max": 320, "y_min": 280, "minimum_patch_score": -0.6},
        "right": {
            "image_size": [640, 360],
            "x_min": 400,
            "y_min": 300,
            "minimum_patch_score": -0.6,
        },
    }:
        raise ValueError("Frozen gate geometry changed")
    by_id = {row["shot_id"]: row for row in origins["rows"]}
    selected = [
        row
        for row in shots["shots"]
        if INTERVAL[0] <= sum(row["interval_s"]) / 2 < INTERVAL[1]
        and by_id[row["shot_id"]]["predicted"]
    ]
    if len(selected) != 17 or selected[0]["shot_id"] != "S460" or selected[-1]["shot_id"] != "S521":
        raise ValueError("Predeclared end-7 origin selection changed")
    model = load_model(MODEL)
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    step = round(fps / 5)
    if fps <= 0 or step < 1:
        raise ValueError("Invalid source frame rate")
    output_rows = []
    for shot in selected:
        start, stop = shot["interval_s"]
        first, last = ceil(start * fps), ceil(stop * fps)
        capture.set(cv2.CAP_PROP_POS_FRAMES, first)
        observations = {side: {colour: [] for colour in ("red", "yellow")} for side in gates}
        samples = {side: [] for side in gates}
        for frame_index in range(first, last):
            if not capture.grab():
                raise RuntimeError(f"Decode failed at frame {frame_index}")
            if frame_index % step:
                continue
            ok, frame = capture.retrieve()
            if not ok:
                raise RuntimeError(f"Retrieve failed at frame {frame_index}")
            t = round(frame_index / fps, 3)
            scored = {
                colour: score_candidates(
                    frame,
                    stone_cap_candidates(
                        frame, colour, allow_bright_body=True, allow_large_caps=True
                    ),
                    model,
                )
                for colour in ("red", "yellow")
            }
            for side, gate in gates.items():
                chosen = {}
                for colour in scored:
                    chosen[colour] = [
                        row
                        for row in scored[colour]
                        if row["pixel"][1] >= gate["y_min"]
                        and row["patch_score"] >= gate["minimum_patch_score"]
                        and (
                            row["pixel"][0] <= gate["x_max"]
                            if side == "left"
                            else row["pixel"][0] >= gate["x_min"]
                        )
                    ]
                    observations[side][colour].append((t, chosen[colour]))
                samples[side].append({"time_s": t, "gate_candidates": chosen})
        row = {"shot_id": shot["shot_id"], "interval_s": shot["interval_s"]}
        for side in gates:
            counts = Counter(
                colour
                for sample in samples[side]
                for colour in ("red", "yellow")
                for _ in sample["gate_candidates"][colour]
            )
            row[side] = {
                "gate_counts": {colour: counts[colour] for colour in ("red", "yellow")},
                "transits": {
                    colour: short_transits(observations[side][colour])
                    for colour in ("red", "yellow")
                },
                "samples": samples[side],
            }
        output_rows.append(row)
        if len(output_rows) % 5 == 0:
            print(f"Scanned {len(output_rows)}/{len(selected)} origin shots", flush=True)
    capture.release()
    result = {
        "status": "source_only_first_end7_mirrored_gate_scan_not_event_score",
        "source_sha256": source_hash,
        "shot_manifest_sha256": digest(SHOTS),
        "origin_sha256": digest(ORIGINS),
        "model_sha256": digest(MODEL),
        "frozen_gate_sha256": {"left": digest(FROZEN_LEFT), "right": digest(FROZEN_RIGHT)},
        "frozen_router_sha256": digest(FROZEN_ROUTER),
        "runner_sha256": digest(Path(__file__)),
        "selection_interval_s": list(INTERVAL),
        "selection_rule": "All frozen origin-positive shots whose midpoint falls in the end-7 partition; both gates evaluated without reading counters or official colours.",
        "sample_rate_hz": fps / step,
        "origin_positive_count": len(output_rows),
        "gates": gates,
        "rows": output_rows,
        "limitations": [
            "Gate geometry and router were chosen on exposed ends four and five of the same match.",
            "End partition is prior diagnostic context and does not establish physical throw boundaries.",
            "This artifact contains visual evidence only; no counter or official shot information enters detection.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print({"origin_positives": len(output_rows)})


if __name__ == "__main__":
    main()
