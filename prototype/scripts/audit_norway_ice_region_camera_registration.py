"""Check ice-like-region registration for every frozen Norway cap track."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from camera_relative_motion import longest_relative_motion_run  # noqa: E402
from ice_region_camera_registration import ice_region_composed_residual  # noqa: E402
from scripts.audit_china_2022_cap_continuation_scale_transfer import (  # noqa: E402
    reconstructed_tracks,
)

BASE = ROOT / "validation"
VIDEO = BASE / "throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
CATALOG = BASE / "official-shot-sequence/norway-global-shot-scoped-cap-motion-first.json"
PRIOR = BASE / "official-shot-sequence/norway-subframe-cap-track-registration-development.json"
OUT = BASE / "official-shot-sequence/norway-ice-region-cap-track-registration-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def cue_for_pairs(pairs):
    reliable = [row["camera_residual_px"] for row in pairs if row["camera_residual_px"] is not None]
    run = longest_relative_motion_run(pairs, min_residual_px=5)
    if run >= 2:
        return "sustained_camera_relative_motion_cue", run
    if reliable and max(reliable) <= 5:
        return "weak_camera_relative_motion_cue", run
    return "abstain_insufficient_or_mixed_registration", run


def main():
    if OUT.exists():
        raise ValueError("Norway ice-region audit already exists")
    catalog = json.loads(CATALOG.read_text())
    prior = json.loads(PRIOR.read_text())
    source_hash = digest(VIDEO)
    if (
        catalog["source_video_sha256"] != source_hash
        or prior["source_video_sha256"] != source_hash
        or prior["catalog_sha256"] != digest(CATALOG)
    ):
        raise ValueError("Source/catalog/subframe lineage differs")
    by_prior = {row["episode_id"]: row for row in prior["rows"]}
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
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
                old = by_prior[eid]
                point_by_time = {point["time_s"]: point for point in points_by_id[eid]}
                pairs = []
                for old_pair in old["pairs"]:
                    before_time, after_time = old_pair["interval_s"]
                    before = point_by_time[before_time]
                    after = point_by_time[after_time]
                    result = ice_region_composed_residual(
                        before["pixel"],
                        after["pixel"],
                        before_time,
                        after_time,
                        frame_at,
                        nominal_step_s=0.25,
                    )
                    pairs.append(
                        {
                            "interval_s": old_pair["interval_s"],
                            "whole_frame_subframe_residual_px": old_pair["camera_residual_px"],
                            "camera_residual_px": result["camera_residual_px"],
                            "status": result["status"],
                            "subpairs": result["subpairs"],
                        }
                    )
                cue, run = cue_for_pairs(pairs)
                rows.append(
                    {
                        "episode_id": eid,
                        "camera_shot_id": shot["camera_shot_id"],
                        "colour": track["colour"],
                        "whole_frame_subframe_cue": old["subframe_cue"],
                        "ice_region_cue": cue,
                        "pair_count": len(pairs),
                        "whole_frame_reliable_pair_count": old["subframe_reliable_pair_count"],
                        "ice_region_reliable_pair_count": sum(
                            pair["camera_residual_px"] is not None for pair in pairs
                        ),
                        "longest_ice_region_relative_motion_run": run,
                        "pairs": pairs,
                        "physical_stone_identity_verified": False,
                    }
                )
            frames.clear()
    finally:
        capture.release()
    if len(rows) != catalog["episode_count"] or len({row["episode_id"] for row in rows}) != len(
        rows
    ):
        raise ValueError("Norway track inventory differs")
    cue_counts = Counter(row["ice_region_cue"] for row in rows)
    cross = Counter((row["whole_frame_subframe_cue"], row["ice_region_cue"]) for row in rows)
    output = {
        "status": "all_norway_ice_like_region_registration_development_not_stone_truth",
        "source_video_sha256": source_hash,
        "catalog_sha256": digest(CATALOG),
        "prior_subframe_audit_sha256": digest(PRIOR),
        "runner_sha256": digest(Path(__file__)),
        "ice_region_code_sha256": digest(ROOT / "prototype/ice_region_camera_registration.py"),
        "method": "Same frozen 1010 point pairs, 0.25 s subframes and 5 px/two-pair cue; estimate each affine fit only from largest connected ice-like region covering at least 20% of frame after 41-pixel morphological closing, with interpolated candidate target excluded by 30 pixels; all subpairs must register.",
        "track_count": len(rows),
        "cue_counts": dict(cue_counts),
        "whole_frame_to_ice_region_cue": [
            {"whole_frame_cue": old, "ice_region_cue": new, "track_count": count}
            for (old, new), count in sorted(cross.items())
        ],
        "rows": rows,
        "limitations": [
            "The ice-like mask is an HSV/morphology heuristic, not a calibrated or independently validated rink-plane segmentation.",
            "The 20% coverage threshold was selected after reviewing exposed Norway frames; this is not held-out accuracy.",
            "Printed artwork, bright clothing, sideboard and connected foreground can contaminate the mask.",
            "A missing cue does not mean no stone moved; a sustained cue does not prove stone identity or a throw event.",
        ],
    }
    OUT.write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {
                "tracks": len(rows),
                "whole_frame_reliable_pairs": sum(
                    r["whole_frame_reliable_pair_count"] for r in rows
                ),
                "ice_region_reliable_pairs": sum(r["ice_region_reliable_pair_count"] for r in rows),
                "cue_counts": dict(cue_counts),
            }
        )
    )


if __name__ == "__main__":
    main()
