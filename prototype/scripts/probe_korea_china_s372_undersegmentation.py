"""Postscore probe of missed internal edits and a second origin inside S372."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from learned_gap_confirmation import compact_overlay_visible  # noqa: E402
from scene_cuts import scene_cut_evidence  # noqa: E402
from shot_origin_model import shot_features  # noqa: E402

BASE = ROOT / "validation/throw-event-benchmark/paralympics-2022-korea-china"
SOURCE = BASE / "source.mp4"
MANIFEST = (
    ROOT
    / "validation/curlobserver-learned-probe/korea-china-full-first-transfer/shot-review/manifest.json"
)
ORIGINS = (
    ROOT / "validation/curlobserver-learned-probe/korea-china-full-first-transfer/shot-origin.json"
)
MODEL = (
    ROOT / "validation/curlobserver-learned-probe/shot-origin-pair-v1/model-excluding-swiss-dev.npz"
)
OUTPUT = BASE / "S372-UNDERSEGMENTATION-PROBE.json"
SPLITS = (5180.6, 5195.6)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def frame_at(cap, fps, t):
    cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
    ok, frame = cap.read()
    if not ok:
        raise RuntimeError(f"Frame decode failed at {t}")
    return frame


def shot_samples(cap, fps, start, end):
    duration = end - start
    times = [
        start + min(0.6, duration * 0.2),
        start + duration * 0.5,
        end - min(0.6, duration * 0.2),
    ]
    frames = [frame_at(cap, fps, t) for t in times]
    return {
        "interval_s": [start, end],
        "frame_times_s": [round(t, 3) for t in times],
        "feature": shot_features(frames),
        "overlay_fraction": sum(compact_overlay_visible(frame) for frame in frames) / 3,
    }


def score_pairs(shots, model):
    blank = np.zeros_like(shots[0]["feature"])
    rows = []
    for index, current in enumerate(shots):
        following = shots[index + 1] if index + 1 < len(shots) else None
        next_feature = following["feature"] if following else blank
        next_live = following["overlay_fraction"] if following else 0
        feature = np.concatenate(
            (current["feature"], next_feature, [current["overlay_fraction"], next_live])
        )
        z = (feature - model["mean"]) / model["scale"]
        logit = float(z @ model["weights"].ravel() + model["intercept"].item())
        probability = float(1 / (1 + np.exp(-np.clip(logit, -40, 40))))
        phase = current["overlay_fraction"] >= 2 / 3 or next_live >= 2 / 3
        rows.append(
            {
                "interval_s": current["interval_s"],
                "frame_times_s": current["frame_times_s"],
                "overlay_fraction": current["overlay_fraction"],
                "following_overlay_fraction": next_live,
                "origin_probability": round(probability, 6),
                "phase_supported": phase,
                "predicted_origin": bool(probability >= 0.5 and phase),
            }
        )
    return rows


def main():
    if OUTPUT.exists():
        raise SystemExit("S372 diagnostic already exists")
    manifest = json.loads(MANIFEST.read_text())
    origins = json.loads(ORIGINS.read_text())
    source_hash = digest(SOURCE)
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if (
        source_hash != manifest["source_sha256"]
        or source_hash != origins["source_sha256"]
        or source_hash == reserved["source_sha256"]
        or digest(MODEL) != origins["model_sha256"]
    ):
        raise ValueError("Source or frozen origin model differs")
    original = next(row for row in manifest["shots"] if row["id"] == "S372")
    following = next(row for row in manifest["shots"] if row["id"] == "S373")
    prior = next(row for row in origins["rows"] if row["shot_id"] == "S372")
    if original["interval_s"] != [5170.8, 5206.2] or following["interval_s"] != [5206.2, 5229.0]:
        raise ValueError("Selected shot boundaries differ")
    cap = cv2.VideoCapture(str(SOURCE), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    try:
        edits = []
        for t in SPLITS:
            evidence = scene_cut_evidence(frame_at(cap, fps, t - 0.2), frame_at(cap, fps, t))
            edits.append(
                {
                    "time_s": t,
                    **evidence,
                    "passes_bounded_0_30_hist_probe": bool(
                        evidence["gray_change"] >= 45 and evidence["hist_distance"] >= 0.30
                    ),
                }
            )
        boundaries = [
            *original["interval_s"][:1],
            *SPLITS,
            original["interval_s"][1],
            following["interval_s"][1],
        ]
        shots = [shot_samples(cap, fps, a, b) for a, b in zip(boundaries, boundaries[1:])]
    finally:
        cap.release()
    with np.load(MODEL, allow_pickle=False) as data:
        model = {key: data[key] for key in data.files}
        scores = score_pairs(shots, model)
    result = {
        "status": "postscore_selected_internal_edit_origin_probe_not_event_validation",
        "source_video_sha256": source_hash,
        "input_sha256": {
            "shot_manifest": digest(MANIFEST),
            "frozen_origin_predictions": digest(ORIGINS),
            "frozen_origin_model": digest(MODEL),
        },
        "scene_cut_code_sha256": digest(ROOT / "prototype/scene_cuts.py"),
        "origin_feature_code_sha256": digest(ROOT / "prototype/shot_origin_model.py"),
        "runner_sha256": digest(Path(__file__)),
        "original_shot_id": "S372",
        "original_interval_s": original["interval_s"],
        "original_probability": prior["probability"],
        "proposed_internal_edits": edits,
        "subshot_origin_scores": scores,
        "limitations": [
            "Internal edit times were selected after inspecting this exposed event gap; they are not independent cut labels.",
            "A lower 0.30 histogram threshold is only a bounded diagnostic, not a validated full-source cut rule.",
            "Origin probability is a view classifier, not physical release or throw identity.",
            "No first-pass event candidate or official-slot mapping is changed.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        [(row["interval_s"], row["origin_probability"], row["predicted_origin"]) for row in scores]
    )


if __name__ == "__main__":
    main()
