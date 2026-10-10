"""Selected camera-relative diagnostic for the two frozen China fallback cues."""

from hashlib import sha256
import json
from math import ceil
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from camera_relative_motion import sample_track_camera_motion
from cap_patch_verifier import score_candidates
from held_origin_cue import _tracks
from short_cap_transit import short_transits
from stone_motion_fallback import stone_cap_candidates
from stone_patch_detector import load_model

BASE = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1"
FIRST = BASE / "china-nonorigin-phase-v2-first.json"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
MODEL = BASE / "model-excluding-swiss-transfer.npz"
OUTPUT = BASE / "china-nonorigin-camera-relative-postscore.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first selected camera-relative audit")
    first = json.loads(FIRST.read_text())
    source_hash = digest(VIDEO)
    if first["source_sha256"] != source_hash:
        raise ValueError("Source fingerprint mismatch")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash == reserved["source_sha256"]:
        raise ValueError("Reserved source selected")
    model = load_model(MODEL)
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    step = round(fps / 5)
    rows = []
    for candidate in first["candidates"]:
        shot_id = candidate["shot_id"]
        colour = candidate["colour"]
        start, end = candidate["interval_s"]
        beginning, stop = ceil(start * fps), ceil(end * fps)
        capture.set(cv2.CAP_PROP_POS_FRAMES, beginning)
        stream = []
        for frame_index in range(beginning, stop):
            if not capture.grab():
                raise RuntimeError(f"Decode failed: {shot_id} {frame_index}")
            if frame_index % step:
                continue
            ok, frame = capture.retrieve()
            if not ok:
                raise RuntimeError(f"Retrieve failed: {shot_id} {frame_index}")
            raw = stone_cap_candidates(frame, colour,
                                       allow_bright_body=True,
                                       allow_large_caps=True)
            accepted = [row for row in score_candidates(frame, raw, model)
                        if row["patch_score"] >= -0.6]
            stream.append((round(frame_index / fps, 3), accepted))
        transits = short_transits(stream)
        tracks = _tracks(stream)
        frame_cache = {}

        def frame_at(time_s):
            if time_s not in frame_cache:
                capture.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError(f"Frame decode failed: {shot_id} {time_s}")
                frame_cache[time_s] = cv2.resize(frame, (640, 360),
                                                 interpolation=cv2.INTER_AREA)
            return frame_cache[time_s]

        transit_rows = []
        for transit in transits[:3]:
            linked = [track for track in tracks
                      if track[0]["time_s"] == transit["interval_s"][0]
                      and track[0]["pixel"] == transit["first_pixel"]
                      and track[-1]["time_s"] == transit["interval_s"][1]]
            if len(linked) != 1:
                pairs = []
                status = "track_link_abstention"
            else:
                pairs = sample_track_camera_motion(linked[0], frame_at, step_s=0.4)
                status = "registered_pairs" if pairs else "too_short_for_pairs"
            residuals = [pair["camera_residual_px"] for pair in pairs
                         if pair["camera_residual_px"] is not None]
            transit_rows.append({"transit": transit, "status": status,
                                 "pair_count": len(pairs),
                                 "reliable_pair_count": len(residuals),
                                 "reliable_over_10px_count": sum(value > 10
                                                                 for value in residuals),
                                 "max_reliable_residual_px": max(residuals, default=None),
                                 "pairs": pairs})
        rows.append({"shot_id": shot_id, "interval_s": candidate["interval_s"],
                     "candidate_colour": colour,
                     "sampled_frame_count": len(stream),
                     "accepted_patch_count": sum(len(items) for _, items in stream),
                     "transit_count": len(transits),
                     "top_transit_camera_motion": transit_rows})
    capture.release()
    output = {
        "status": "selected_postscore_china_camera_relative_fallback_diagnostic_not_event_score",
        "source_sha256": source_hash,
        "first_transfer_sha256": digest(FIRST),
        "model_sha256": digest(MODEL),
        "cap_verifier_code_sha256": digest(ROOT / "prototype/cap_patch_verifier.py"),
        "camera_motion_code_sha256": digest(ROOT / "prototype/camera_relative_motion.py"),
        "runner_sha256": digest(Path(__file__)),
        "sample_rate_hz": fps / step,
        "rows": rows,
        "limitations": [
            "The two camera shots were selected after the frozen fallback transfer and ledger overlap check.",
            "A stone-like cap track moving relative to registered image features need not be a new delivered stone.",
            "Unreliable registration and missing track links are abstentions, not negative motion evidence.",
            "No official shot or counter label enters the motion calculation.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print([(row["shot_id"], row["transit_count"],
            [(item["status"], item["reliable_pair_count"],
              item["reliable_over_10px_count"], item["max_reliable_residual_px"])
             for item in row["top_transit_camera_motion"]]) for row in rows])


if __name__ == "__main__":
    main()
