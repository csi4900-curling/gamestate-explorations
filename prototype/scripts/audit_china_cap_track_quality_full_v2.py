"""Replay exact transit points in the full China track-quality audit."""

from hashlib import sha256
import json
from math import ceil
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from audit_china_nonorigin_track_continuity import step_shape
from camera_relative_motion import sample_track_camera_motion
from cap_patch_verifier import score_candidates
from short_transit_replay import short_transits_with_points
from stone_motion_fallback import stone_cap_candidates
from stone_patch_detector import load_model

BASE = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1"
FULL = ROOT / "validation/curlobserver-learned-probe/china-full-transfer"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
MODEL = BASE / "model-excluding-swiss-transfer.npz"
CAP = FULL / "two-shot-cap.json"
SHOTS = FULL / "sequential-shot-cap-motion.json"
PRIOR = BASE / "china-cap-track-quality-full-first.json"
PLAN = BASE / "china-cap-track-quality-full-v2-plan.json"
OUTPUT = BASE / "china-cap-track-quality-full-v2-first.json"


def digest(path):
    h = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def planned_windows(cap, shots):
    by_id = {shot["shot_id"]: shot for shot in shots["shots"]}
    return [{"shot_id": row["shot_id"],
             "interval_s": by_id[row["shot_id"]]["interval_s"],
             "colour": row["colour"]}
            for row in cap["decisions"]
            if row["status"] == "corroborated_candidate"]


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve full first track-quality audit")
    plan = json.loads(PLAN.read_text())
    cap = json.loads(CAP.read_text())
    shots = json.loads(SHOTS.read_text())
    hashes = {name: digest(path) for name, path in
              (("video", VIDEO), ("model", MODEL), ("cap", CAP), ("shots", SHOTS),
               ("runner", __file__))}
    if hashes != plan["sha256"] or planned_windows(cap, shots) != plan["windows"]:
        raise ValueError("Frozen plan or source inputs changed")
    if (digest(PRIOR) != plan["prior_first_sha256"] or
            digest(ROOT / "prototype/short_transit_replay.py") !=
            plan["replay_code_sha256"]):
        raise ValueError("Frozen replay or prior result changed")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if hashes["video"] == reserved["source_sha256"]:
        raise ValueError("Reserved independent source selected")
    model = load_model(MODEL)
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    step = round(fps / plan["sample_rate_hz"])
    rows = []
    for window in plan["windows"]:
        shot_id = window["shot_id"]
        if window["colour"] is None:
            rows.append({
                **window, "sampled_frames": 0, "accepted_patch_count": 0,
                "transit_count": 0, "top_transit": None,
                "track_link_status": "unknown_colour",
                "step_shape": None, "camera_pair_count": 0,
                "reliable_camera_pair_count": 0,
                "maximum_camera_residual_px": None,
                "quality": "abstain_unknown_colour",
            })
            continue
        start, end = window["interval_s"]
        beginning, stop = ceil(start * fps), ceil(end * fps)
        capture.set(cv2.CAP_PROP_POS_FRAMES, beginning)
        stream = []
        frames = {}
        for frame_index in range(beginning, stop):
            if not capture.grab():
                raise RuntimeError(f"Decode failed: {shot_id} {frame_index}")
            if frame_index % step:
                continue
            ok, frame = capture.retrieve()
            if not ok:
                raise RuntimeError(f"Retrieve failed: {shot_id} {frame_index}")
            time_s = round(frame_index / fps, 3)
            raw = stone_cap_candidates(frame, window["colour"],
                                       allow_bright_body=True,
                                       allow_large_caps=True)
            accepted = [row for row in score_candidates(frame, raw, model)
                        if row["patch_score"] >= plan["minimum_patch_score"]]
            stream.append((time_s, accepted))
            frames[time_s] = cv2.resize(frame, (640, 360),
                                        interpolation=cv2.INTER_AREA)
        transits = short_transits_with_points(stream)
        shape = None
        pairs = []
        link_status = "no_transit"
        if transits:
            _, points = transits[0]
            link_status = "exact_transit_points"
            shape = step_shape(points)
            pairs = sample_track_camera_motion(points, frames.__getitem__,
                                               step_s=plan["camera_pair_step_s"])
        reliable = [pair["camera_residual_px"] for pair in pairs
                    if pair["camera_residual_px"] is not None]
        distributed = bool(shape and
                           shape["steps_over_5px"] >= plan["minimum_moving_steps"] and
                           shape["largest_step_fraction"] is not None and
                           shape["largest_step_fraction"] <= plan["maximum_step_fraction"])
        if not shape:
            quality = "abstain_no_linked_transit"
        elif not distributed:
            quality = "weak_track_continuity"
        elif not reliable:
            quality = "abstain_no_reliable_camera_pair"
        elif max(reliable) <= plan["minimum_camera_residual_px"]:
            quality = "weak_camera_relative_motion"
        else:
            quality = "combined_cue_supported"
        rows.append({
            **window,
            "sampled_frames": len(stream),
            "accepted_patch_count": sum(len(items) for _, items in stream),
            "transit_count": len(transits),
            "top_transit": transits[0][0] if transits else None,
            "track_link_status": link_status,
            "step_shape": shape,
            "camera_pair_count": len(pairs),
            "reliable_camera_pair_count": len(reliable),
            "maximum_camera_residual_px": max(reliable, default=None),
            "quality": quality,
        })
        if len(rows) % 20 == 0:
            print(f"scanned {len(rows)}/{len(plan['windows'])}", flush=True)
    capture.release()
    output = {
        "status": "first_full_source_only_china_exact_transit_track_quality_audit_not_event_score",
        "sha256": hashes,
        "plan_sha256": digest(PLAN),
        "prior_first_sha256": digest(PRIOR),
        "replay_code_sha256": digest(ROOT / "prototype/short_transit_replay.py"),
        "sample_rate_hz": fps / step,
        "rows": rows,
        "limitations": [
            "China is exposed from prior development; this is a frozen source-only coverage audit, not held-out validation.",
            "Only the top short transit per cap-corroborated shot is checked; another transit may be the delivered stone.",
            "Candidates with unknown colour abstain without image rescanning.",
            "This version fixes an audit-only second-tracker mismatch by using exact short-transit points.",
            "Weak or absent local track evidence does not prove the underlying event is false.",
            "No counter colour, official shot, or human event label enters the quality calculation.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    from collections import Counter
    print(dict(Counter(row["quality"] for row in rows)))


if __name__ == "__main__":
    main()
