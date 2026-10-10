"""Transfer the China-developed prior-cap-size gate to 2022 Norway source."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from local_colour_cap_probe import local_cap_components  # noqa: E402
from scripts.audit_china_2022_cap_continuation_scale_transfer import (  # noqa: E402
    reconstructed_tracks, search_roi)
from scripts.compare_china_2022_cap_area_gates import score  # noqa: E402

BASE = ROOT / "validation"
VIDEO = BASE / "throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
CATALOG = BASE / "official-shot-sequence/norway-global-shot-scoped-cap-motion-first.json"
CHINA_SENSITIVITY = BASE / "official-shot-sequence/china-2022-cap-area-gate-sensitivity-development.json"
OUT = BASE / "official-shot-sequence/norway-2022-cap-area-gate-transfer-development.json"
SCALE = 3.0


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Norway prior-area transfer already exists")
    catalog = json.loads(CATALOG.read_text())
    china = json.loads(CHINA_SENSITIVITY.read_text())
    source_hash = digest(VIDEO)
    if (catalog["source_video_sha256"] != source_hash or
            catalog["motion_detector_sha256"] != digest(ROOT /
                                                      "prototype/stone_motion_fallback.py") or
            catalog["runner_sha256"] != digest(ROOT /
                "prototype/scripts/build_norway_global_cap_motion_catalog.py") or
            china["selector_code_sha256"] != digest(ROOT /
                                                    "prototype/causal_cap_continuation.py") or
            china["gate_definitions"]["past_cap_area_0p5_to_2"] !=
            "next contour area between 1/2 and 2 times last observed source cap area"):
        raise ValueError("Norway source or China gate lineage differs")
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not capture.isOpened() or abs(fps - 30) > 0.01:
        raise ValueError("Norway source unreadable or FPS changed")
    rows = []
    try:
        for shot in catalog["shots"]:
            if not shot["tracks"]:
                continue
            by_id = reconstructed_tracks(capture, fps, shot)
            for track in shot["tracks"]:
                points = by_id[track["episode_id"]]
                next_time = points[-1]["time_s"] + 0.5
                boundary = next_time >= shot["interval_s"][1]
                row = {
                    "episode_id": track["episode_id"],
                    "camera_shot_id": shot["camera_shot_id"],
                    "colour": track["colour"],
                    "camera_shot_interval_s": shot["interval_s"],
                    "last_two_reconstructed_points_360": points[-2:],
                    "next_sample_time_s": next_time,
                    "shot_boundary_abstention": boundary,
                    "raw_colour_components": [],
                    "absolute_area_decision": None,
                    "past_cap_area_0p5_to_2_decision": None,
                    "persistent_stone_identity_verified": False,
                }
                if not boundary:
                    previous = [v * SCALE for v in points[-2]["pixel"]]
                    current = [v * SCALE for v in points[-1]["pixel"]]
                    ratio = 0.5 / (points[-1]["time_s"] - points[-2]["time_s"])
                    predicted = [current[i] +
                                 (current[i] - previous[i]) * ratio
                                 for i in (0, 1)]
                    roi = search_roi([v / SCALE for v in predicted],
                                     shape=(360, 640), radius=30)
                    frame_index = round(next_time * fps)
                    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                    ok, frame = capture.read()
                    if not ok or frame.shape[:2] != (360, 640):
                        raise ValueError("Norway source frame unreadable")
                    row.update({
                        "decoded_frame_index": frame_index,
                        "search_roi_xyxy_px_360": list(roi),
                        "raw_colour_components": local_cap_components(
                            frame, roi, track["colour"],
                            minimum_area_px2=20 / SCALE**2),
                    })
                    row["absolute_area_decision"] = score(row, None)
                    row["past_cap_area_0p5_to_2_decision"] = score(
                        row, (0.5, 2))
                rows.append(row)
    finally:
        capture.release()
    if (len(rows) != catalog["episode_count"] or
            len({r["episode_id"] for r in rows}) != len(rows)):
        raise ValueError("Norway shot-scoped track inventory differs")
    counts = Counter("camera_shot_boundary" if r[
        "shot_boundary_abstention"] else r[
        "past_cap_area_0p5_to_2_decision"]["status"] for r in rows)
    baseline = Counter("camera_shot_boundary" if r[
        "shot_boundary_abstention"] else r[
        "absolute_area_decision"]["status"] for r in rows)
    result = {
        "status": "china_developed_prior_cap_area_norway_transfer_not_identity_truth",
        "source_video_sha256": source_hash,
        "input_sha256": {"norway_shot_cap_catalog": digest(CATALOG),
                         "china_area_gate_selection": digest(CHINA_SENSITIVITY)},
        "runner_sha256": digest(Path(__file__)),
        "reconstruction_code_sha256": digest(ROOT /
            "prototype/scripts/audit_china_2022_cap_continuation_scale_transfer.py"),
        "gate_code_sha256": digest(ROOT /
            "prototype/scripts/compare_china_2022_cap_area_gates.py"),
        "selector_code_sha256": digest(ROOT /
                                       "prototype/causal_cap_continuation.py"),
        "component_code_sha256": digest(ROOT /
                                        "prototype/local_colour_cap_probe.py"),
        "method": {
            "source_resolution_px": [640, 360],
            "coordinate_scale_to_czech_reference": SCALE,
            "next_sample_gap_s": 0.5,
            "camera_shot_boundary_is_hard_abstention": True,
            "baseline_absolute_area_source_px2": [20 / 9, 700 / 9],
            "transferred_past_cap_area_ratio": [0.5, 2],
            "hsv_motion_and_gate_thresholds_changed_from_china_audit": False,
        },
        "source_catalog_track_count": len(rows),
        "absolute_gate_status_counts": dict(baseline),
        "past_area_gate_status_counts": dict(counts),
        "rows": rows,
        "limitations": [
            "The size ratio was chosen after the China 2022 failure and applied unchanged here, but the Norway source was exposed in earlier detector development.",
            "Shot-scoped cap tracks are candidate image paths, not independently labelled physical throws or stone identities.",
            "One additional in-shot half-second cap step does not validate complete trajectories, game state or simulation readiness.",
            "A larger count of unique geometric choices could include wrong objects and requires source-pixel review before promotion.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"tracks": len(rows),
                      "absolute": dict(baseline),
                      "past_area": dict(counts)}))


if __name__ == "__main__":
    main()
