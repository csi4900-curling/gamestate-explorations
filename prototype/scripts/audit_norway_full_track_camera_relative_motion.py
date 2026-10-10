"""Audit all frozen Norway cap paths against same-shot camera registration."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from camera_relative_motion import (  # noqa: E402
    longest_relative_motion_run,
    sample_track_camera_motion,
)
from scripts.audit_china_2022_cap_continuation_scale_transfer import (  # noqa: E402
    reconstructed_tracks,
)

BASE = ROOT / "validation"
VIDEO = BASE / "throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
CATALOG = BASE / "official-shot-sequence/norway-global-shot-scoped-cap-motion-first.json"
TRANSFER = BASE / "official-shot-sequence/norway-2022-cap-area-gate-transfer-development.json"
OUT = BASE / "official-shot-sequence/norway-full-cap-track-camera-relative-motion-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Norway camera-relative audit already exists")
    catalog = json.loads(CATALOG.read_text())
    transfer = json.loads(TRANSFER.read_text())
    source_hash = digest(VIDEO)
    if (
        catalog["source_video_sha256"] != source_hash
        or transfer["source_video_sha256"] != source_hash
        or transfer["input_sha256"]["norway_shot_cap_catalog"] != digest(CATALOG)
        or catalog["motion_detector_sha256"] != digest(ROOT / "prototype/stone_motion_fallback.py")
    ):
        raise ValueError("Norway source or catalog lineage differs")
    transfer_by_id = {row["episode_id"]: row for row in transfer["rows"]}
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        raise ValueError("Source video unreadable")
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for shot in catalog["shots"]:
            if not shot["tracks"]:
                continue
            by_id = reconstructed_tracks(capture, fps, shot)
            frames = {}

            def frame_at(time_s):
                if time_s not in frames:
                    capture.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
                    ok, frame = capture.read()
                    if not ok or frame.shape[:2] != (360, 640):
                        raise ValueError(f"Norway source frame unreadable: {time_s}")
                    frames[time_s] = frame
                return frames[time_s]

            for track in shot["tracks"]:
                eid = track["episode_id"]
                points = by_id[eid]
                pairs = sample_track_camera_motion(points, frame_at)
                reliable = [
                    pair["camera_residual_px"]
                    for pair in pairs
                    if pair["camera_residual_px"] is not None
                ]
                run = longest_relative_motion_run(pairs, min_residual_px=5)
                if run >= 2:
                    cue = "sustained_camera_relative_motion_cue"
                elif reliable and max(reliable) <= 5:
                    cue = "weak_camera_relative_motion_cue"
                else:
                    cue = "abstain_insufficient_or_mixed_registration"
                source = transfer_by_id[eid]
                rows.append(
                    {
                        "episode_id": eid,
                        "colour": track["colour"],
                        "camera_shot_id": shot["camera_shot_id"],
                        "point_count": len(points),
                        "source_interval_s": track["interval_s"],
                        "span_px": track["span_px"],
                        "camera_pair_count": len(pairs),
                        "reliable_camera_pair_count": len(reliable),
                        "maximum_reliable_residual_px": max(reliable, default=None),
                        "longest_relative_motion_run": run,
                        "camera_relative_cue": cue,
                        "prior_area_next_step_status": (
                            "camera_shot_boundary"
                            if source["shot_boundary_abstention"]
                            else source["past_cap_area_0p5_to_2_decision"]["status"]
                        ),
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
    counts = Counter(row["camera_relative_cue"] for row in rows)
    cross = Counter(
        (row["prior_area_next_step_status"], row["camera_relative_cue"]) for row in rows
    )
    result = {
        "status": "all_norway_frozen_cap_tracks_camera_relative_diagnostic_not_event_or_identity_truth",
        "source_video_sha256": source_hash,
        "catalog_sha256": digest(CATALOG),
        "transfer_sha256": digest(TRANSFER),
        "runner_sha256": digest(Path(__file__)),
        "reconstruction_code_sha256": digest(
            ROOT / "prototype/scripts/audit_china_2022_cap_continuation_scale_transfer.py"
        ),
        "camera_relative_code_sha256": digest(ROOT / "prototype/camera_relative_motion.py"),
        "method": "Exact source reconstruction of all shot-scoped 1 Hz cap paths; existing similarity registration on approximately 1 s point pairs; sustained cue requires two consecutive reliable residuals >5 source pixels.",
        "track_count": len(rows),
        "cue_counts": dict(counts),
        "cue_by_next_step": [
            {"next_step": status, "cue": cue, "track_count": count}
            for (status, cue), count in sorted(cross.items())
        ],
        "rows": rows,
        "limitations": [
            "Camera registration may be supported by foreground instead of ice or fail on low-texture ice.",
            "Weak terminal motion does not mean an earlier path was false; the full-path pairs are retained for review.",
            "Unknown registration stays unknown and cannot safely veto a candidate.",
            "Camera-relative movement does not by itself identify a physical stone or a throw event.",
            "The Norway source was exposed in earlier detector development; no independent F1 follows.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"tracks": len(rows), "cue_counts": dict(counts)}))


if __name__ == "__main__":
    main()
