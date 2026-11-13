"""Apply frozen Norway camera-registration variants to all China cap tracks."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from camera_relative_motion import sample_track_camera_motion  # noqa: E402
from subframe_camera_registration import composed_residual  # noqa: E402
from ice_region_camera_registration import ice_region_composed_residual  # noqa: E402
from scripts.audit_china_2022_cap_continuation_scale_transfer import (  # noqa: E402
    reconstructed_tracks,
)
from scripts.audit_norway_ice_region_camera_registration import (  # noqa: E402
    cue_for_pairs,
)

BASE = ROOT / "validation"
VIDEO = BASE / "throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
CATALOG = BASE / "official-shot-sequence/china-global-shot-scoped-cap-motion-first.json"
NORWAY_SUBFRAME = (
    BASE / "official-shot-sequence/norway-subframe-cap-track-registration-development.json"
)
NORWAY_ICE = (
    BASE / "official-shot-sequence/norway-ice-region-cap-track-registration-development.json"
)
OUT = (
    BASE
    / "official-shot-sequence/china-ice-region-cap-track-registration-transfer-development.json"
)


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("China registration transfer already exists")
    catalog = json.loads(CATALOG.read_text())
    norway_sub = json.loads(NORWAY_SUBFRAME.read_text())
    norway_ice = json.loads(NORWAY_ICE.read_text())
    source_hash = digest(VIDEO)
    reserved = json.loads((BASE / "unseen-end/reservation.json").read_text())
    if source_hash == reserved["source_sha256"]:
        raise ValueError("Reserved independent source cannot be used for development")
    if (
        catalog["source_video_sha256"] != source_hash
        or catalog["motion_detector_sha256"] != digest(ROOT / "prototype/stone_motion_fallback.py")
        or catalog["shared_shot_track_code_sha256"]
        != digest(ROOT / "prototype/scripts/build_norway_global_cap_motion_catalog.py")
        or norway_sub["subframe_code_sha256"]
        != digest(ROOT / "prototype/subframe_camera_registration.py")
        or norway_ice["ice_region_code_sha256"]
        != digest(ROOT / "prototype/ice_region_camera_registration.py")
        or norway_ice["prior_subframe_audit_sha256"] != digest(NORWAY_SUBFRAME)
    ):
        raise ValueError("China catalog or Norway-frozen rule lineage differs")
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        raise ValueError("China source unreadable")
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
                        raise ValueError(f"China frame unreadable: {frame_index}")
                    frames[frame_index] = frame
                return frames[frame_index]

            for track in shot["tracks"]:
                eid = track["episode_id"]
                points = points_by_id[eid]
                direct = sample_track_camera_motion(points, frame_at)
                point_by_time = {point["time_s"]: point for point in points}
                subframe = []
                ice_region = []
                for old in direct:
                    before_time, after_time = old["interval_s"]
                    before = point_by_time[before_time]
                    after = point_by_time[after_time]
                    sub = composed_residual(
                        before["pixel"],
                        after["pixel"],
                        before_time,
                        after_time,
                        frame_at,
                        nominal_step_s=0.25,
                    )
                    ice = ice_region_composed_residual(
                        before["pixel"],
                        after["pixel"],
                        before_time,
                        after_time,
                        frame_at,
                        nominal_step_s=0.25,
                    )
                    subframe.append(
                        {
                            "interval_s": old["interval_s"],
                            "camera_residual_px": sub["camera_residual_px"],
                            "status": sub["status"],
                            "subpairs": sub["subpairs"],
                        }
                    )
                    ice_region.append(
                        {
                            "interval_s": old["interval_s"],
                            "camera_residual_px": ice["camera_residual_px"],
                            "status": ice["status"],
                            "subpairs": ice["subpairs"],
                        }
                    )
                direct_cue, direct_run = cue_for_pairs(direct)
                sub_cue, sub_run = cue_for_pairs(subframe)
                ice_cue, ice_run = cue_for_pairs(ice_region)
                rows.append(
                    {
                        "episode_id": eid,
                        "camera_shot_id": shot["camera_shot_id"],
                        "colour": track["colour"],
                        "source_interval_s": track["interval_s"],
                        "span_px": track["span_px"],
                        "point_count": len(points),
                        "pair_count": len(direct),
                        "direct_reliable_pair_count": sum(
                            pair["camera_residual_px"] is not None for pair in direct
                        ),
                        "subframe_reliable_pair_count": sum(
                            pair["camera_residual_px"] is not None for pair in subframe
                        ),
                        "ice_region_reliable_pair_count": sum(
                            pair["camera_residual_px"] is not None for pair in ice_region
                        ),
                        "direct_cue": direct_cue,
                        "subframe_cue": sub_cue,
                        "ice_region_cue": ice_cue,
                        "direct_longest_motion_run": direct_run,
                        "subframe_longest_motion_run": sub_run,
                        "ice_region_longest_motion_run": ice_run,
                        "direct_pairs": direct,
                        "subframe_pairs": subframe,
                        "ice_region_pairs": ice_region,
                        "physical_stone_identity_verified": False,
                    }
                )
                if len(rows) % 20 == 0:
                    print(f"transferred {len(rows)}/{catalog['episode_count']} tracks", flush=True)
            frames.clear()
    finally:
        capture.release()
    if len(rows) != catalog["episode_count"] or len({row["episode_id"] for row in rows}) != len(
        rows
    ):
        raise ValueError("China frozen track inventory differs")
    cue_counts = {
        name: dict(Counter(row[f"{name}_cue"] for row in rows))
        for name in ("direct", "subframe", "ice_region")
    }
    output = {
        "status": "norway_developed_registration_rules_china_transfer_not_identity_truth",
        "source_video_sha256": source_hash,
        "catalog_sha256": digest(CATALOG),
        "norway_subframe_audit_sha256": digest(NORWAY_SUBFRAME),
        "norway_ice_region_audit_sha256": digest(NORWAY_ICE),
        "runner_sha256": digest(Path(__file__)),
        "reconstruction_code_sha256": digest(
            ROOT / "prototype/scripts/audit_china_2022_cap_continuation_scale_transfer.py"
        ),
        "direct_code_sha256": digest(ROOT / "prototype/camera_relative_motion.py"),
        "subframe_code_sha256": digest(ROOT / "prototype/subframe_camera_registration.py"),
        "ice_region_code_sha256": digest(ROOT / "prototype/ice_region_camera_registration.py"),
        "cue_code_sha256": digest(
            ROOT / "prototype/scripts/audit_norway_ice_region_camera_registration.py"
        ),
        "method": "All exact frozen 1 Hz China shot-scoped cap paths; identical Norway point-pair selector; unchanged direct 1 s, all-reliable 0.25 s chaining, and broad ice-like-region registration; unchanged 5 px residual and two-pair sustained cue.",
        "track_count": len(rows),
        "pair_count": sum(row["pair_count"] for row in rows),
        "cue_counts": cue_counts,
        "rows": rows,
        "limitations": [
            "China is a second exposed 2022 broadcast recording, not an independently held-out event benchmark.",
            "A cap path may be a person, old stone, graphic or camera artifact; motion cues do not establish physical identity.",
            "Ice-like image-region selection is not a calibrated rink plane and can fail in new view types.",
            "No throw-event precision or recall, complete game state, or simulation-ready trajectory is inferred.",
        ],
    }
    OUT.write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {
                "tracks": len(rows),
                "pairs": output["pair_count"],
                "reliable_pairs": {
                    name: sum(row[f"{name}_reliable_pair_count"] for row in rows)
                    for name in ("direct", "subframe", "ice_region")
                },
                "cue_counts": cue_counts,
            }
        )
    )


if __name__ == "__main__":
    main()
