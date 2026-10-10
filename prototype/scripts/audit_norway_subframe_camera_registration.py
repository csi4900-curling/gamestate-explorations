"""Transfer 0.25 s chained registration to every frozen Norway cap path."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from camera_relative_motion import longest_relative_motion_run  # noqa: E402
from subframe_camera_registration import composed_residual  # noqa: E402
from scripts.audit_china_2022_cap_continuation_scale_transfer import (  # noqa: E402
    reconstructed_tracks)

BASE = ROOT / "validation"
VIDEO = BASE / "throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
CATALOG = BASE / "official-shot-sequence/norway-global-shot-scoped-cap-motion-first.json"
PRIOR = BASE / "official-shot-sequence/norway-full-cap-track-camera-relative-motion-development.json"
OUT = BASE / "official-shot-sequence/norway-subframe-cap-track-registration-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def cue_for_pairs(pairs):
    reliable = [row["camera_residual_px"] for row in pairs
                if row["camera_residual_px"] is not None]
    run = longest_relative_motion_run(pairs, min_residual_px=5)
    if run >= 2:
        return "sustained_camera_relative_motion_cue", run
    if reliable and max(reliable) <= 5:
        return "weak_camera_relative_motion_cue", run
    return "abstain_insufficient_or_mixed_registration", run


def main():
    if OUT.exists():
        raise ValueError("Norway subframe audit already exists")
    catalog = json.loads(CATALOG.read_text())
    prior = json.loads(PRIOR.read_text())
    source_hash = digest(VIDEO)
    if (catalog["source_video_sha256"] != source_hash or
            prior["source_video_sha256"] != source_hash or
            prior["catalog_sha256"] != digest(CATALOG)):
        raise ValueError("Source/catalog/prior lineage differs")
    by_prior = {row["episode_id"]: row for row in prior["rows"]}
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        raise ValueError("Norway source unreadable")
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for shot in catalog["shots"]:
            if not shot["tracks"]:
                continue
            points_by_id = reconstructed_tracks(capture, fps, shot)
            frames = {}

            def frame_at(time_s):
                frame_index = round(time_s * fps)
                if frame_index not in frames:
                    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                    ok, frame = capture.read()
                    if not ok or frame.shape[:2] != (360, 640):
                        raise ValueError(f"Frame unreadable: {frame_index}")
                    frames[frame_index] = frame
                return frames[frame_index]

            for track in shot["tracks"]:
                eid = track["episode_id"]
                prior_row = by_prior[eid]
                point_by_time = {point["time_s"]: point
                                 for point in points_by_id[eid]}
                pairs = []
                for old in prior_row["pairs"]:
                    before_time, after_time = old["interval_s"]
                    before = point_by_time[before_time]
                    after = point_by_time[after_time]
                    result = composed_residual(
                        before["pixel"], after["pixel"],
                        before_time, after_time, frame_at,
                        nominal_step_s=0.25)
                    pairs.append({
                        "interval_s": old["interval_s"],
                        "direct_one_second_residual_px": old["camera_residual_px"],
                        "camera_residual_px": result["camera_residual_px"],
                        "status": result["status"],
                        "subpairs": result["subpairs"],
                    })
                cue, run = cue_for_pairs(pairs)
                rows.append({
                    "episode_id": eid,
                    "camera_shot_id": shot["camera_shot_id"],
                    "colour": track["colour"],
                    "prior_cue": prior_row["camera_relative_cue"],
                    "subframe_cue": cue,
                    "pair_count": len(pairs),
                    "direct_reliable_pair_count": prior_row[
                        "reliable_camera_pair_count"],
                    "subframe_reliable_pair_count": sum(
                        pair["camera_residual_px"] is not None for pair in pairs),
                    "longest_subframe_relative_motion_run": run,
                    "pairs": pairs,
                    "physical_stone_identity_verified": False,
                })
            frames.clear()
    finally:
        capture.release()
    if (len(rows) != catalog["episode_count"] or
            len({row["episode_id"] for row in rows}) != len(rows)):
        raise ValueError("Norway track inventory differs")
    cue_counts = Counter(row["subframe_cue"] for row in rows)
    cross = Counter((row["prior_cue"], row["subframe_cue"]) for row in rows)
    result = {
        "status": "all_norway_chained_subframe_registration_development_not_stone_truth",
        "source_video_sha256": source_hash,
        "catalog_sha256": digest(CATALOG),
        "prior_audit_sha256": digest(PRIOR),
        "runner_sha256": digest(Path(__file__)),
        "subframe_code_sha256": digest(ROOT /
                                       "prototype/subframe_camera_registration.py"),
        "camera_relative_code_sha256": digest(ROOT /
                                              "prototype/camera_relative_motion.py"),
        "method": "Exactly the 1010 previously selected full-track point pairs; chain 0.25 s source-frame similarity transforms only if every subpair meets existing reliability rule; 5 px residual and two-pair run cue unchanged.",
        "track_count": len(rows),
        "cue_counts": dict(cue_counts),
        "prior_to_subframe_cue": [
            {"prior_cue": old, "subframe_cue": new, "track_count": count}
            for (old, new), count in sorted(cross.items())],
        "rows": rows,
        "limitations": [
            "The 0.25 s interval was chosen after reviewing selected Norway frames and this exposed recording is not independent validation.",
            "All-subpair reliability prevents gap bridging but can still fit foreground features rather than rink-plane motion.",
            "A camera-relative cue is not stone identity, event detection, throw F1, or a simulation-ready trajectory.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"tracks": len(rows),
                      "direct_reliable_pairs": sum(r["direct_reliable_pair_count"] for r in rows),
                      "subframe_reliable_pairs": sum(r["subframe_reliable_pair_count"] for r in rows),
                      "cue_counts": dict(cue_counts)}))


if __name__ == "__main__":
    main()
