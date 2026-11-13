"""Finish the aggregate pipeline using checked within-shot calibration transfer.

Accepts completed or incrementally written tracking evidence. Every event is kept.
No labels enter this stage. Per-event hashes permit safe streaming and resumption.
"""

import argparse
from collections import defaultdict
from functools import lru_cache
import json
from pathlib import Path
import sys
import time
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from aggregate_trajectory import bounded_segments, sample_segment, summarize
from camera_geometry import calibrate_sequence
from cache_contract import file_sha256
from integrated_trajectory import (
    assess_track, link_segments, reject_reused_tracks, orient_image_aligned_samples,
)
from vision_core import project


def extend(video, evidence_dir, output, expected_events, *, events_path, wait=False):
    cv2.setNumThreads(2)
    cv2.setRNGSeed(0)
    source_hash = file_sha256(video)
    original_events = json.loads(events_path.read_text())
    if original_events["source_sha256"] != source_hash:
        raise ValueError("Event/source mismatch")
    original_count = len(original_events.get("observed_events", original_events.get("events", [])))
    if original_count != expected_events:
        raise ValueError("Final stage must retain every input candidate")
    code = [
        "prototype/scripts/extend_registered_trajectories.py",
        "prototype/camera_geometry.py",
        "prototype/automatic_house_calibration.py",
        "prototype/integrated_trajectory.py",
        "prototype/aggregate_trajectory.py",
        "prototype/vision_core.py",
        "prototype/rectification_core.py",
        "prototype/cross_view.py",
    ]
    config = {
        "source_sha256": source_hash,
        "code_sha256": {p: file_sha256(ROOT / p) for p in code},
        "opencv": cv2.__version__,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    cache = output.parent / (output.stem + "-events")
    cache.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise ValueError("Cannot open source")

    @lru_cache(maxsize=128)
    def frame(t):
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, f = cap.read()
        if not ok:
            raise RuntimeError(f"Cannot decode {t}")
        return cv2.resize(f, (640, 360))

    results = []
    contexts = []
    tracking_context = (
        {"source_sha256": source_hash, "events_sha256": file_sha256(events_path)}
        if not expected_events
        else None
    )
    for index in range(expected_events):
        input_path = evidence_dir / "aggregate-events" / f"{index:04}.json"
        while not input_path.exists():
            if not wait:
                raise ValueError(f"Missing tracking evidence {input_path}")
            time.sleep(2)
        # Inference writes a small JSON file once; wait for an in-progress write only.
        for retry in range(10):
            try:
                raw = json.loads(input_path.read_text())
                break
            except json.JSONDecodeError:
                if not wait or retry == 9:
                    raise
                time.sleep(0.2)
        if raw["context"]["source_sha256"] != source_hash:
            raise ValueError("Tracking/source mismatch")
        if raw["context"]["events_sha256"] != file_sha256(events_path):
            raise ValueError("Tracking/event fingerprint mismatch")
        if tracking_context is None:
            tracking_context = raw["context"]
        if tracking_context != raw["context"]:
            raise ValueError("Mixed tracking contexts")
        context = {**config, "tracking_event_sha256": file_sha256(input_path)}
        contexts.append(context)
        cached = cache / f"{index:04}.json"
        if cached.exists():
            saved = json.loads(cached.read_text())
            if saved["context"] != context:
                raise ValueError("Changed input or code; use new output")
            results.append(saved["event"])
            continue
        event = raw["event"]
        event["segments"] = [s for s in event["segments"] if s["camera"] == "left_split"]
        event["failure_reasons"] = [
            r
            for r in event["failure_reasons"]
            if not r.startswith(
                (
                    "no_supported_stone_track:",
                    "ambiguous_stone_identity:",
                    "cross_view_identity_unresolved",
                )
            )
        ]
        by_camera = defaultdict(list)
        for h in event["motion_hypotheses"]:
            support = sum("learned" in p.get("channels", []) for p in h["pixel_points"]) / len(
                h["pixel_points"]
            )
            if support >= 0.5:
                by_camera[h["camera"]].append(h)
        rebuilt = []
        for camera, hs in by_camera.items():
            region = (320, 70, 640, 360) if camera == "right_split" else (0, 70, 640, 360)
            times = sorted(
                {
                    p["time_s"]
                    for h in hs
                    for p in sample_segment(h["pixel_points"], hz=1)
                    if "learned" in p.get("channels", [])
                }
            )
            initial = {}
            for h in hs:
                for g in h["geometry_samples"]:
                    if g["top_view_m"] is not None:
                        initial[g["time_s"]] = (
                            np.array(g["homography_source_pixels_to_local_metres"]),
                            g.get("calibration", {}),
                        )
            cuts = sorted({t for h in hs for t in h.get("camera_cut_times_s", [])})
            geometry = calibrate_sequence(
                {t: frame(t) for t in times}, region, cuts, initial=initial
            )
            eligible = []
            for h in hs:
                samples = []
                for p in sample_segment(h["pixel_points"], hz=1):
                    g = {
                        "time_s": p["time_s"],
                        "pixel": p["pixel"],
                        "top_view_m": None,
                        "rink_position_m": None,
                        "homography_source_pixels_to_local_metres": None,
                        "status": "stone_appearance_not_corroborated",
                    }
                    if "learned" in p.get("channels", []):
                        H, diag = geometry[p["time_s"]]
                        g["calibration"] = diag
                        g["status"] = diag.get("status", "geometry_failed")
                        if H is not None:
                            try:
                                xy = project(H, [p["pixel"]])[0]
                                if abs(xy[0]) <= 2.375 and abs(xy[1]) <= 32:
                                    g.update(
                                        top_view_m=xy.tolist(),
                                        homography_source_pixels_to_local_metres=H.tolist(),
                                        status="image_supported_ice_plane_projection",
                                    )
                                else:
                                    g["status"] = "outside_nominal_rink_bounds"
                            except ValueError:
                                g["status"] = "invalid_planar_projection"
                    samples.append(g)
                orientation = orient_image_aligned_samples(samples, h["role"])
                evidence = assess_track({"points": h["pixel_points"]}, samples)
                h = {
                    **h,
                    "geometry_samples": samples,
                    "association_evidence": evidence,
                    "orientation_status": orientation,
                    "associated": False,
                }
                rebuilt.append(h)
                if evidence["eligible"]:
                    eligible.append(h)
            if len(eligible) == 1:
                h = eligible[0]
                h["associated"] = True
                supported = [p for p in h["pixel_points"] if "learned" in p.get("channels", [])]
                groups, _ = bounded_segments(supported, max_duration_s=60, max_gap_s=1.1)
                for group in groups:
                    if len(group) < 2:
                        continue
                    gs = [
                        g
                        for g in h["geometry_samples"]
                        if group[0]["time_s"] <= g["time_s"] <= group[-1]["time_s"]
                    ]
                    event["segments"].append({**h, "pixel_points": group, "geometry_samples": gs})
            else:
                event["failure_reasons"].append(
                    ("ambiguous_stone_identity:" if eligible else "no_supported_stone_track:")
                    + camera
                )
        event["motion_hypotheses"] = rebuilt
        for n, s in enumerate(event["segments"]):
            s["segment_id"] = f"{event['candidate_id']}:{n}"
        event["cross_view_links"] = link_segments(event["segments"])
        if not event["cross_view_links"]:
            event["failure_reasons"].append("cross_view_identity_unresolved")
        cached.write_text(json.dumps({"context": context, "event": event}) + "\n")
        results.append(event)
        print(
            f"final geometry {index + 1}/{expected_events} {event['candidate_id']}: {len(event['segments'])} segments",
            flush=True,
        )
    cap.release()
    reject_reused_tracks(results)
    summary = summarize(results)
    summary["events_with_cross_view_link"] = sum(bool(e["cross_view_links"]) for e in results)
    result = {
        "schema_version": "aggregate-throw-v3",
        "context": {
            **config,
            "events_sha256": tracking_context["events_sha256"],
            "tracking_context": tracking_context,
            "tracking_event_sha256": [c["tracking_event_sha256"] for c in contexts],
        },
        "source_interval_s": original_events["source_interval_s"],
        "events": results,
        "summary": summary,
        "limitations": [
            "Projected cap positions use an ice-plane model.",
            "Image-registration extension requires a supported house anchor within 3 seconds, fresh correspondences and no camera cut.",
            "Cross-view identities and orientation are provisional; unobserved travel is not interpolated.",
        ],
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--evidence-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--expected-events", type=int, required=True)
    p.add_argument("--events", type=Path, required=True)
    p.add_argument("--wait", action="store_true")
    a = p.parse_args()
    extend(a.video, a.evidence_dir, a.output, a.expected_events, events_path=a.events, wait=a.wait)
