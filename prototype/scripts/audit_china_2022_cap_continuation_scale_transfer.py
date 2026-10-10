"""Audit one board-blind cap step across all 2022 China shot-scoped tracks."""

from collections import Counter
from hashlib import sha256
import json
from math import ceil
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from causal_cap_continuation import choose_next_cap  # noqa: E402
from local_colour_cap_probe import local_cap_components  # noqa: E402
from scripts.build_norway_global_cap_motion_catalog import summary  # noqa: E402
from scripts.extend_czech_reviewed_stone_caps import search_roi  # noqa: E402
from stone_motion_fallback import moving_cap_tracks, stone_cap_candidates  # noqa: E402

BASE = ROOT / "validation"
VIDEO = BASE / "throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
CATALOG = BASE / "official-shot-sequence/china-global-shot-scoped-cap-motion-first.json"
OUT = BASE / "official-shot-sequence/china-2022-cap-continuation-scale-transfer-development.json"
SCALE = 3.0  # 640 x 360 source pixels expressed on the Czech 1920 x 1080 grid.


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def reconstructed_tracks(video, fps, shot):
    observations = {"red": [], "yellow": []}
    for second in range(ceil(shot["interval_s"][0]), ceil(shot["interval_s"][1])):
        video.set(cv2.CAP_PROP_POS_FRAMES, round(second * fps))
        ok, frame = video.read()
        if not ok or frame.shape[:2] != (360, 640):
            raise ValueError(f"Source frame unreadable: {second}")
        for colour in observations:
            observations[colour].append((float(second), stone_cap_candidates(frame, colour)))
    rows = {}
    summaries = []
    for colour in ("red", "yellow"):
        tracks = moving_cap_tracks(observations[colour])
        for index, track in enumerate(tracks, start=1):
            info = summary(track, shot["camera_shot_id"], colour, index)
            rows[info["episode_id"]] = track["points"]
            summaries.append(info)
    if summaries != shot["tracks"]:
        raise ValueError(
            f"Shot-scoped source track reconstruction differs: {shot['camera_shot_id']}"
        )
    return rows


def main():
    if OUT.exists():
        raise ValueError("2022 scale-transfer audit already exists")
    catalog = json.loads(CATALOG.read_text())
    video_hash = digest(VIDEO)
    if (
        catalog["source_video_sha256"] != video_hash
        or catalog["motion_detector_sha256"] != digest(ROOT / "prototype/stone_motion_fallback.py")
        or catalog["shared_shot_track_code_sha256"]
        != digest(ROOT / "prototype/scripts/build_norway_global_cap_motion_catalog.py")
    ):
        raise ValueError("2022 source or frozen track lineage differs")
    video = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = video.get(cv2.CAP_PROP_FPS)
    if not video.isOpened() or abs(fps - 30) > 0.01:
        raise ValueError("2022 source unreadable or FPS changed")
    rows = []
    try:
        for shot in catalog["shots"]:
            if not shot["tracks"]:
                continue
            points_by_id = reconstructed_tracks(video, fps, shot)
            for track in shot["tracks"]:
                points = points_by_id[track["episode_id"]]
                last_time = points[-1]["time_s"]
                next_time = last_time + 0.5
                row = {
                    "episode_id": track["episode_id"],
                    "camera_shot_id": shot["camera_shot_id"],
                    "colour": track["colour"],
                    "camera_shot_interval_s": shot["interval_s"],
                    "last_catalog_time_s": last_time,
                    "source_catalog_last_pixel_360": track["last_pixel"],
                    "last_two_reconstructed_points_360": points[-2:],
                    "next_sample_time_s": next_time,
                    "shot_boundary_abstention": next_time >= shot["interval_s"][1],
                    "decision": None,
                    "raw_colour_components": [],
                    "area_scaled_components": [],
                    "persistent_stone_identity_verified": False,
                }
                if not row["shot_boundary_abstention"]:
                    previous = [v * SCALE for v in points[-2]["pixel"]]
                    current = [v * SCALE for v in points[-1]["pixel"]]
                    ratio = 0.5 / (last_time - points[-2]["time_s"])
                    predicted = [current[i] + (current[i] - previous[i]) * ratio for i in (0, 1)]
                    roi = search_roi([v / SCALE for v in predicted], shape=(360, 640), radius=30)
                    frame_index = round(next_time * fps)
                    video.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                    ok, frame = video.read()
                    if not ok or frame.shape[:2] != (360, 640):
                        raise ValueError(f"2022 source frame unreadable: {frame_index}")
                    raw = local_cap_components(
                        frame, roi, track["colour"], minimum_area_px2=20 / SCALE**2
                    )
                    eligible = [c for c in raw if c["area_px2"] <= 700 / SCALE**2]
                    scaled = [
                        {
                            **c,
                            "centroid_px_1080": [
                                round(v * SCALE, 3) for v in c["centroid_px_1080"]
                            ],
                        }
                        for c in eligible
                    ]
                    decision = choose_next_cap(current, previous, ratio, scaled)
                    row.update(
                        {
                            "decoded_frame_index": frame_index,
                            "search_roi_xyxy_px_360": list(roi),
                            "raw_colour_components": raw,
                            "area_scaled_components": eligible,
                            "decision": decision,
                        }
                    )
                rows.append(row)
    finally:
        video.release()
    if len(rows) != catalog["episode_count"] or len({r["episode_id"] for r in rows}) != len(rows):
        raise ValueError("2022 cap track inventory not conserved")
    statuses = Counter(
        "camera_shot_boundary" if r["shot_boundary_abstention"] else r["decision"]["status"]
        for r in rows
    )
    result = {
        "status": "2022_china_one_step_scale_transfer_development_not_identity_truth",
        "source_video_sha256": video_hash,
        "input_sha256": {"shot_scoped_cap_catalog": digest(CATALOG)},
        "runner_sha256": digest(Path(__file__)),
        "selector_code_sha256": digest(ROOT / "prototype/causal_cap_continuation.py"),
        "component_code_sha256": digest(ROOT / "prototype/local_colour_cap_probe.py"),
        "source_track_code_sha256": digest(ROOT / "prototype/stone_motion_fallback.py"),
        "method": {
            "source_resolution_px": [640, 360],
            "czech_reference_resolution_px": [1920, 1080],
            "coordinate_scale_to_reference": SCALE,
            "contour_area_scale_to_source": 1 / SCALE**2,
            "next_sample_gap_s": 0.5,
            "camera_shot_boundary_is_hard_abstention": True,
            "czech_hsv_and_motion_gate_parameters_changed": False,
            "resolution_scaling_is_geometry_only": True,
        },
        "source_catalog_track_count": len(rows),
        "status_counts": dict(statuses),
        "rows": rows,
        "limitations": [
            "The 2022 source was exposed during prior event development, and its shot-scoped cap catalog is not a physical throw reference.",
            "This is a one-half-second continuation probe, not a complete trajectory or settled-board association.",
            "Resolution scaling alone does not compensate for camera zoom, cap size, appearance, motion blur or source cuts.",
            "A geometrically selected cap may be another object; none of these rows verifies persistent stone identity, event F1 or simulation readiness.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"tracks": len(rows), "statuses": dict(statuses)}))


if __name__ == "__main__":
    main()
