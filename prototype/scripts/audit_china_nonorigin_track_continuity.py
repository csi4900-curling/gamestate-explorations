"""Postscore track-continuity and missed-edit audit of frozen China fallback cues."""

from hashlib import sha256
import json
from math import ceil, dist
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cap_patch_verifier import score_candidates
from held_origin_cue import _tracks
from scene_cuts import scene_cut_evidence
from short_cap_transit import short_transits
from stone_motion_fallback import stone_cap_candidates
from stone_patch_detector import load_model

BASE = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1"
FIRST = BASE / "china-nonorigin-phase-v2-first.json"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
MODEL = BASE / "model-excluding-swiss-transfer.npz"
OUTPUT = BASE / "china-nonorigin-track-continuity-postscore.json"


def digest(path):
    h = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def step_shape(track):
    steps = [dist(a["pixel"], b["pixel"]) for a, b in zip(track, track[1:])]
    path = sum(steps)
    largest_index = max(range(len(steps)), key=steps.__getitem__) if steps else None
    return {
        "point_count": len(track),
        "interval_s": [track[0]["time_s"], track[-1]["time_s"]],
        "path_px": round(path, 2),
        "largest_step_px": round(steps[largest_index], 2) if steps else 0,
        "largest_step_fraction": round(steps[largest_index] / path, 3) if steps and path else None,
        "largest_step_interval_s": [
            track[largest_index]["time_s"],
            track[largest_index + 1]["time_s"],
        ]
        if steps
        else None,
        "steps_over_5px": sum(step >= 5 for step in steps),
    }


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve selected first continuity audit")
    first = json.loads(FIRST.read_text())
    source_hash = digest(VIDEO)
    if first["source_sha256"] != source_hash:
        raise ValueError("Source fingerprint mismatch")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash == reserved["source_sha256"]:
        raise ValueError("Reserved source selected")
    model = load_model(MODEL)
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    step = round(fps / 5)
    rows = []
    for candidate in first["candidates"]:
        shot_id = candidate["shot_id"]
        start, end = candidate["interval_s"]
        beginning, stop = ceil(start * fps), ceil(end * fps)
        capture.set(cv2.CAP_PROP_POS_FRAMES, beginning)
        stream = []
        changes = []
        previous = None
        for frame_index in range(beginning, stop):
            if not capture.grab():
                raise RuntimeError(f"Decode failed: {shot_id} {frame_index}")
            if frame_index % step:
                continue
            ok, frame = capture.retrieve()
            if not ok:
                raise RuntimeError(f"Retrieve failed: {shot_id} {frame_index}")
            time_s = round(frame_index / fps, 3)
            raw = stone_cap_candidates(
                frame, candidate["colour"], allow_bright_body=True, allow_large_caps=True
            )
            accepted = [
                row for row in score_candidates(frame, raw, model) if row["patch_score"] >= -0.6
            ]
            stream.append((time_s, accepted))
            if previous is not None:
                changes.append({"time_s": time_s, **scene_cut_evidence(previous, frame)})
            previous = frame
        tracks = _tracks(stream)
        transits = short_transits(stream)
        transit_tracks = []
        for transit in transits[:3]:
            linked = [
                track
                for track in tracks
                if track[0]["time_s"] == transit["interval_s"][0]
                and track[0]["pixel"] == transit["first_pixel"]
                and track[-1]["time_s"] == transit["interval_s"][1]
            ]
            transit_tracks.append(
                {
                    "transit": transit,
                    "linked_track_count": len(linked),
                    "step_shape": step_shape(linked[0]) if len(linked) == 1 else None,
                }
            )
        changes.sort(key=lambda row: row["gray_change"] * row["hist_distance"], reverse=True)
        rows.append(
            {
                "shot_id": shot_id,
                "interval_s": candidate["interval_s"],
                "sampled_frame_count": len(stream),
                "internal_hard_cut_count": sum(row["hard_cut"] for row in changes),
                "top_frame_changes": changes[:5],
                "transit_tracks": transit_tracks,
                "longest_tracks": [
                    step_shape(track) for track in sorted(tracks, key=len, reverse=True)[:3]
                ],
            }
        )
    capture.release()
    output = {
        "status": "selected_postscore_track_continuity_and_edit_diagnostic_not_event_score",
        "source_sha256": source_hash,
        "first_transfer_sha256": digest(FIRST),
        "model_sha256": digest(MODEL),
        "scene_cut_code_sha256": digest(ROOT / "prototype/scene_cuts.py"),
        "runner_sha256": digest(__file__),
        "sample_rate_hz": fps / step,
        "rows": rows,
        "limitations": [
            "Only two fallback camera shots, selected after the frozen transfer, are scanned.",
            "A dominant association step is suspicious but does not prove a false stone track.",
            "Frame-change peaks below the frozen hard-cut threshold are possible edits, not certified cuts.",
            "No official shot, counter or physical release label enters this diagnostic.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(
        [
            (
                row["shot_id"],
                row["internal_hard_cut_count"],
                row["top_frame_changes"][0]["time_s"],
                row["transit_tracks"][0]["step_shape"],
            )
            for row in rows
        ]
    )


if __name__ == "__main__":
    main()
