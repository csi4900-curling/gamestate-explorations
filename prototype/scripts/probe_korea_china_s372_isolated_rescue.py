"""Source-only postscore rescue check after an isolated internal edit in S372."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from audit_full_shot_cap_motion import tracks_for_shot  # noqa: E402
from probe_korea_china_s372_undersegmentation import (score_pairs, shot_samples)  # noqa: E402
from shot_transition_confirmation import confirm_shot_transitions  # noqa: E402
from stone_motion_fallback import stone_cap_candidates  # noqa: E402

BASE = ROOT / "validation/throw-event-benchmark/paralympics-2022-korea-china"
SOURCE = BASE / "source.mp4"
EVIDENCE = ROOT / "validation/curlobserver-learned-probe/korea-china-full-first-transfer"
MANIFEST = EVIDENCE / "shot-review/manifest.json"
ORIGINS = EVIDENCE / "shot-origin.json"
LEDGER = EVIDENCE / "candidate-event-ledger.json"
EDITS = EVIDENCE / "possible-edits-0_30-temporal.json"
MODEL = ROOT / "validation/curlobserver-learned-probe/shot-origin-pair-v1/model-excluding-swiss-dev.npz"
OUTPUT = BASE / "S372-ISOLATED-CUT-RESCUE.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Selected rescue probe already exists")
    manifest = json.loads(MANIFEST.read_text())
    origins = json.loads(ORIGINS.read_text())
    ledger = json.loads(LEDGER.read_text())
    edits = json.loads(EDITS.read_text())
    source_hash = digest(SOURCE)
    if (len({source_hash, manifest["source_sha256"], origins["source_sha256"],
             ledger["source_sha256"], edits["source_sha256"]}) != 1 or
            origins["model_sha256"] != digest(MODEL)):
        raise ValueError("Frozen source or origin model differs")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash == reserved["source_sha256"]:
        raise ValueError("Reserved source selected")
    original = next(row for row in manifest["shots"] if row["id"] == "S372")
    next_shot = next(row for row in manifest["shots"] if row["id"] == "S373")
    selected = [row for row in edits["rows"] if row["shot_id"] == "S372" and
                row["isolated_spike"]]
    if (original["interval_s"] != [5170.8, 5206.2] or
            next_shot["interval_s"] != [5206.2, 5229.0] or
            [row["time_s"] for row in selected] != [5195.6]):
        raise ValueError("Selected isolated cut or shot boundaries differ")
    split = selected[0]["time_s"]
    segments = [("S372A", 5170.8, split), ("S372B", split, 5206.2),
                ("S373", 5206.2, 5229.0)]
    cap = cv2.VideoCapture(str(SOURCE), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    try:
        sampled = [shot_samples(cap, fps, a, b) for _, a, b in segments]
        tracks = []
        for shot_id, start, end in segments:
            observations = {"red": [], "yellow": []}
            for tick in range(round(start * 5), round(end * 5)):
                t = round(tick / 5, 3)
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f"Frame decode failed at {t}")
                for colour in observations:
                    observations[colour].append((t, stone_cap_candidates(
                        frame, colour, allow_bright_body=True,
                        allow_large_caps=True)))
            tracks.append(tracks_for_shot(observations, shot_id))
    finally:
        cap.release()
    with np.load(MODEL, allow_pickle=False) as data:
        model = {key: data[key] for key in data.files}
        scores = score_pairs(sampled, model)
    predictions = [{"shot_id": shot_id, "predicted": score["predicted_origin"]}
                   for (shot_id, _, _), score in zip(segments, scores)]
    motion_rows = [{"shot_id": shot_id,
                    "same_shot_candidates": tracks[i],
                    "following_shot_candidates": tracks[i + 1]
                    if i + 1 < len(tracks) else []}
                   for i, (shot_id, _, _) in enumerate(segments)]
    decisions = confirm_shot_transitions(predictions, {"cap": motion_rows})
    original_candidate = next(row for row in ledger["events"]
                              if row["shot_id"] == "S372")
    result = {
        "status": "postscore_selected_isolated_cut_second_origin_candidate_not_verified_throw",
        "source_video_sha256": source_hash,
        "input_sha256": {"shot_manifest": digest(MANIFEST),
                         "frozen_origins": digest(ORIGINS),
                         "frozen_candidate_ledger": digest(LEDGER),
                         "possible_edit_temporal_audit": digest(EDITS),
                         "frozen_origin_model": digest(MODEL)},
        "code_sha256": {
            "origin_feature": digest(ROOT / "prototype/shot_origin_model.py"),
            "cap_tracker": digest(ROOT / "prototype/stone_motion_fallback.py"),
            "two_shot_confirmation": digest(ROOT / "prototype/shot_transition_confirmation.py"),
            "shot_scoring_helper": digest(ROOT / "prototype/scripts/probe_korea_china_s372_undersegmentation.py"),
            "runner": digest(Path(__file__))},
        "original_camera_shot_id": "S372",
        "original_camera_shot_interval_s": original["interval_s"],
        "original_candidate_id": original_candidate["candidate_id"],
        "original_candidate_colour": original_candidate["colour"],
        "isolated_edit_time_s": split,
        "subshot_origin_scores": [dict(shot_id=shot_id, **score)
                                  for (shot_id, _, _), score in zip(segments, scores)],
        "subshot_cap_motion": motion_rows,
        "two_shot_decisions": decisions,
        "limitations": [
            "S372 was selected after comparing exposed first predictions with the official shot count and source frames.",
            "The 0.30 edit-candidate threshold was tuned on this case; an isolated image change is not a certified broadcast cut.",
            "Red cap motion can be player clothing or another stone; two-shot colour agreement does not prove physical identity.",
            "This sidecar does not mutate the frozen 103-event ledger, assign an official shot, or establish event F1.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print([(row["shot_id"], row["status"], row["colour"])
           for row in decisions])


if __name__ == "__main__":
    main()
