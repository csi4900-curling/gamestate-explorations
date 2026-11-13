"""Replay one frozen source path pair through each layout registration route."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from layout_camera_motion import source_camera_relative_pair  # noqa: E402
from scripts.audit_china_2022_cap_continuation_scale_transfer import (  # noqa: E402
    reconstructed_tracks,
)

BASE = ROOT / "validation/throw-event-benchmark"
CHINA_VIDEO = BASE / "paralympics-2022-canada-china/source.mp4"
CHINA_PREFLIGHT = BASE / "layout-router/camera-motion-route-china22-485-505/preflight.json"
CHINA_CATALOG = (
    ROOT / "validation/official-shot-sequence/china-global-shot-scoped-cap-motion-first.json"
)
CHINA_PRIOR = (
    ROOT
    / "validation/official-shot-sequence/china-ice-region-cap-track-registration-transfer-development.json"
)
CZECH_VIDEO = BASE / "canada-czech-2024/source-1080p-full-format270.mp4"
CZECH_PREFLIGHT = BASE / "layout-router/camera-motion-route-czech24-95-115/preflight.json"
CZECH_LOW_VIDEO = BASE / "canada-czech-2024/source-360p.mp4"
CZECH_LOW_PREFLIGHT = BASE / "layout-router/camera-motion-route-czech24-360p-95-115/preflight.json"
CZECH_PATHS = BASE / "canada-czech-2024/full-reviewed-stone-replay-gaps-development.json"
CZECH_PRIOR = (
    BASE
    / "canada-czech-2024/split-panel-registration-reviewed-paths-edge-guard-v2-development.json"
)
CZECH_LOW_PRIOR = (
    BASE
    / "canada-czech-2024/lowres-split-registration-positive-and-board-controls-development.json"
)
OUT = BASE / "layout-router/camera-motion-route-two-layouts-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def frame_source(video):
    cap = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise ValueError(f"Video unreadable: {video}")
    fps = cap.get(cv2.CAP_PROP_FPS)

    def frame_at(time_s):
        index = round(time_s * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = cap.read()
        if not ok:
            raise ValueError(f"Frame {index} unreadable: {video}")
        return frame

    return cap, fps, frame_at


def main():
    if OUT.exists():
        raise ValueError("Layout-camera route audit already exists")
    china_pre = json.loads(CHINA_PREFLIGHT.read_text())
    czech_pre = json.loads(CZECH_PREFLIGHT.read_text())
    czech_low_pre = json.loads(CZECH_LOW_PREFLIGHT.read_text())
    china_catalog = json.loads(CHINA_CATALOG.read_text())
    china_prior = json.loads(CHINA_PRIOR.read_text())
    czech_paths = json.loads(CZECH_PATHS.read_text())
    czech_prior = json.loads(CZECH_PRIOR.read_text())
    czech_low_prior = json.loads(CZECH_LOW_PRIOR.read_text())
    if (
        china_pre["source_sha256"] != digest(CHINA_VIDEO)
        or czech_pre["source_sha256"] != digest(CZECH_VIDEO)
        or czech_low_pre["source_sha256"] != digest(CZECH_LOW_VIDEO)
        or czech_paths["source_video_sha256"] != czech_low_pre["source_sha256"]
        or china_catalog["source_video_sha256"] != china_pre["source_sha256"]
        or china_prior["catalog_sha256"] != digest(CHINA_CATALOG)
        or china_prior["ice_region_code_sha256"]
        != digest(ROOT / "prototype/ice_region_camera_registration.py")
        or czech_prior["reviewed_ledger_sha256"] != digest(CZECH_PATHS)
        or czech_prior["source_sha256"] != czech_pre["source_sha256"]
        or czech_prior["registration_code_sha256"]
        != digest(ROOT / "prototype/split_panel_camera_registration.py")
        or czech_low_prior["source_video_sha256"] != czech_low_pre["source_sha256"]
        or czech_low_prior["lowres_adapter_sha256"]
        != digest(ROOT / "prototype/lowres_split_panel_camera_registration.py")
    ):
        raise ValueError("Frozen source, path or registration lineage differs")
    rows = []
    capture, fps, frame_at = frame_source(CHINA_VIDEO)
    try:
        shot = next(
            s
            for s in china_catalog["shots"]
            if any(track["episode_id"] == "S37-Y01" for track in s["tracks"])
        )
        points = reconstructed_tracks(capture, fps, shot)["S37-Y01"]
        by_time = {p["time_s"]: p["pixel"] for p in points}
        expected = next(r for r in china_prior["rows"] if r["episode_id"] == "S37-Y01")
        expected_pair = next(
            p for p in expected["ice_region_pairs"] if p["interval_s"] == [492.0, 493.0]
        )
        routed = source_camera_relative_pair(
            china_pre,
            china_pre["source_sha256"],
            by_time[492.0],
            by_time[493.0],
            492.0,
            493.0,
            frame_at,
        )
        if (
            routed["camera_residual_px"] != expected_pair["camera_residual_px"]
            or routed["layout"] != "beijing_2022"
        ):
            raise ValueError("China route changed frozen pair result")
        rows.append(
            {
                "source": "paralympics-2022-canada-china",
                "path_id": "S37-Y01",
                "interval_s": [492.0, 493.0],
                "source_pixels": [by_time[492.0], by_time[493.0]],
                "route": routed,
            }
        )
    finally:
        capture.release()
    capture, _, frame_at = frame_source(CZECH_VIDEO)
    try:
        points = next(r for r in czech_paths["rows"] if r["episode_id"] == "E001")[
            "observed_left_motion_path"
        ]
        by_time = {p["source_time_s"]: p["pixel_center_1080"] for p in points}
        expected = next(r for r in czech_prior["rows"] if r["episode_id"] == "E001")
        expected_pair = next(p for p in expected["pairs"] if p["interval_s"] == [100.0, 100.5])
        routed = source_camera_relative_pair(
            czech_pre,
            czech_pre["source_sha256"],
            by_time[100.0],
            by_time[100.5],
            100.0,
            100.5,
            frame_at,
        )
        if (
            routed["camera_residual_px"] != expected_pair["camera_residual_px"]
            or routed["layout"] != "split_2024"
            or routed["panel"] != "right"
        ):
            raise ValueError("Czech route changed frozen pair result")
        rows.append(
            {
                "source": "canada-czech-2024",
                "path_id": "E001",
                "interval_s": [100.0, 100.5],
                "source_pixels": [by_time[100.0], by_time[100.5]],
                "route": routed,
            }
        )
    finally:
        capture.release()
    capture, _, frame_at = frame_source(CZECH_LOW_VIDEO)
    try:
        lower_pixels = [
            [value / 3 for value in point] for point in (by_time[100.0], by_time[100.5])
        ]
        routed = source_camera_relative_pair(
            czech_low_pre,
            czech_low_pre["source_sha256"],
            lower_pixels[0],
            lower_pixels[1],
            100.0,
            100.5,
            frame_at,
        )
        expected_low = next(
            r
            for r in czech_low_prior["rows"]
            if r["group"] == "reviewed_moving_path"
            and r["id"] == "E001"
            and r["interval_s"] == [100.0, 100.5]
        )
        if (
            routed["camera_residual_px"] != expected_low["lowres"]["camera_residual_px"]
            or routed["layout"] != "split_2024"
            or routed["panel"] != "right"
        ):
            raise ValueError("360p split route changed frozen pair result")
        rows.append(
            {
                "source": "canada-czech-2024-low-resolution",
                "path_id": "E001",
                "interval_s": [100.0, 100.5],
                "source_pixels": lower_pixels,
                "route": routed,
            }
        )
    finally:
        capture.release()
    payload = {
        "status": "layout_aware_camera_motion_source_replay_not_throw_accuracy",
        "input_sha256": {
            "china_source": digest(CHINA_VIDEO),
            "china_preflight": digest(CHINA_PREFLIGHT),
            "china_catalog": digest(CHINA_CATALOG),
            "china_prior_registration": digest(CHINA_PRIOR),
            "czech_source": digest(CZECH_VIDEO),
            "czech_preflight": digest(CZECH_PREFLIGHT),
            "czech_low_source": digest(CZECH_LOW_VIDEO),
            "czech_low_preflight": digest(CZECH_LOW_PREFLIGHT),
            "czech_reviewed_paths": digest(CZECH_PATHS),
            "czech_prior_registration": digest(CZECH_PRIOR),
            "czech_low_prior_registration": digest(CZECH_LOW_PRIOR),
        },
        "router_code_sha256": digest(ROOT / "prototype/layout_camera_motion.py"),
        "lowres_adapter_sha256": digest(
            ROOT / "prototype/lowres_split_panel_camera_registration.py"
        ),
        "layout_preflight_code_sha256": digest(ROOT / "prototype/layout_preflight.py"),
        "runner_sha256": digest(Path(__file__)),
        "rows": rows,
        "limitations": [
            "The three accepted reviewed pairs are selected source-path checks, not coverage or throw-event validation.",
            "Preflight chunks are sparse layout evidence and do not prove continuous camera coverage.",
            "A camera-relative residual does not identify a physical stone, release, settle, or game state.",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(
        json.dumps(
            {
                r["source"]: {
                    "layout": r["route"]["layout"],
                    "residual_px": r["route"]["camera_residual_px"],
                }
                for r in rows
            }
        )
    )


if __name__ == "__main__":
    main()
