"""Complete frozen/new event outputs with tracks, homographies and failure records.

Called by both event runners. Also accepts existing frozen outputs without
rerunning or changing their detector decisions. Writes a separate aggregate
artifact; source labels never enter inference.
"""

import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from aggregate_trajectory import bounded_segments, sample_segment, summarize
from cache_contract import file_sha256
from rectification_core import validate_rings
from scene_cuts import scene_cut_evidence
from stone_motion_fallback import moving_cap_tracks, stone_cap_candidates
from vision_core import ViewCalibrator, project


def read_frame(capture, t):
    capture.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, frame = capture.read()
    if not ok:
        raise RuntimeError(f"Source decode failed at {t}")
    return cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)


def recover_shot_tracks(capture, shot, cache):
    """Recover discarded within-camera coordinates with the existing cap detector."""
    key = shot["id"]
    if key in cache:
        return cache[key]
    observations = {"red": [], "yellow": []}
    start, end = shot["interval_s"]
    fps = capture.get(cv2.CAP_PROP_FPS)
    first, last = round(start * fps), round(end * fps)
    step = max(1, round(fps / 5))
    capture.set(cv2.CAP_PROP_POS_FRAMES, first)
    for index in range(first, last):
        if not capture.grab():
            raise RuntimeError(f"Source decode failed at frame {index}")
        if (index - first) % step:
            continue
        ok, frame = capture.retrieve()
        if not ok:
            raise RuntimeError(f"Source retrieve failed at frame {index}")
        t = round(index / fps, 3)
        for colour in observations:
            observations[colour].append(
                (
                    t,
                    stone_cap_candidates(
                        frame, colour, allow_bright_body=True, allow_large_caps=True
                    ),
                )
            )
    tracks = []
    for colour, samples in observations.items():
        for track in moving_cap_tracks(samples, max_gap_s=1.6, max_step_px=130):
            tracks.append({**track, "colour": colour, "camera_shot_id": key})
    cache[key] = tracks
    return tracks


def make_calibrator():
    cfg = json.loads((ROOT / "prototype/vision/annotations/calibration.json").read_text())["views"][
        "left"
    ]
    cal = ViewCalibrator(cfg, ROOT / "prototype/vision/frames")
    cal.H = np.array(
        json.loads((ROOT / "prototype/rectification/calibration.json").read_text())["left"][
            "refined_H"
        ]
    )
    return cal, cfg


def project_sample(frame, point, cal, cfg):
    large = cv2.resize(frame, (1920, 1080), interpolation=cv2.INTER_LINEAR)
    H, registration = cal.register(large)
    result = {
        "time_s": point["time_s"],
        "pixel": point["pixel"],
        "top_view_m": None,
        "homography_source_pixels_to_local_metres": None,
        "status": "registration_failed",
        "registration": registration,
    }
    if H is None:
        return result
    # Feature agreement alone is insufficient; test the painted rings too.
    accepted, rings = validate_rings(large, H, cfg["region"])
    result["ring_check"] = rings
    result["status"] = "ring_geometry_failed"
    if not accepted:
        return result
    source_H = H @ np.diag([3.0, 3.0, 1.0])
    xy = project(source_H, [point["pixel"]])[0]
    if not (-2.375 <= xy[0] <= 2.375 and -32.0 <= xy[1] <= 2.0):
        result["status"] = "outside_nominal_rink_bounds"
        return result
    result.update(
        status="image_supported_ice_plane_projection",
        top_view_m=xy.tolist(),
        homography_source_pixels_to_local_metres=source_H.tolist(),
        outside_calibration_landmark_footprint=bool(np.linalg.norm(xy) > 1.829),
    )
    return result


def complete(
    video,
    events_path,
    output,
    *,
    motion_review=None,
    integrated=True,
    base=None,
    learned_model=None,
):
    if integrated:
        raw_events = json.loads(events_path.read_text())
        split_events = raw_events.get("observed_events", raw_events.get("events", []))
        if split_events and all("observed_track_points" in e for e in split_events):
            from split_pipeline import complete_split

            return complete_split(video, events_path, output, base=base)
        from integrated_trajectory import complete_integrated, DEFAULT_MODEL
        from scripts.extend_registered_trajectories import extend

        raw = json.loads(events_path.read_text())
        candidates = raw.get("observed_events", raw.get("events", []))
        # The established departure stage retains its camera-cut and gap handling.
        if base is None and any("observed_track_points" in e for e in candidates):
            base = output.parent / "departure-evidence" / "aggregate.json"
            complete(video, events_path, base, motion_review=motion_review, integrated=False)
        tracking_dir = output.parent / "tracking-evidence"
        complete_integrated(
            video,
            events_path,
            tracking_dir / "aggregate.json",
            motion_review=motion_review,
            base=base,
            learned_model=learned_model or DEFAULT_MODEL,
        )
        registered_output = output.parent / "registered-evidence" / "aggregate.json"
        result = extend(
            video, tracking_dir, registered_output, len(candidates), events_path=events_path
        )
        if any("observed_track_points" in e for e in candidates):
            from split_receiving_trajectory import complete_receiving

            return complete_receiving(video, registered_output, output)
        output.write_text(json.dumps(result, indent=2) + "\n")
        return result
    cv2.setNumThreads(2)
    cv2.setRNGSeed(0)
    raw = json.loads(events_path.read_text())
    source_hash = file_sha256(video)
    if raw["source_sha256"] != source_hash:
        raise ValueError("Event predictions and video have different fingerprints")
    context = {
        "source_sha256": source_hash,
        "events_sha256": file_sha256(events_path),
        "code_sha256": {
            name: file_sha256(ROOT / name)
            for name in (
                "prototype/aggregate_trajectory.py",
                "prototype/scripts/complete_throw_trajectories.py",
                "prototype/vision_core.py",
                "prototype/rectification_core.py",
                "prototype/stone_motion_fallback.py",
                "prototype/scene_cuts.py",
                "prototype/vision/annotations/calibration.json",
                "prototype/rectification/calibration.json",
                "prototype/vision/frames/00750.jpg",
            )
        },
        "motion_review_sha256": file_sha256(motion_review) if motion_review else None,
        "geometry_sample_rate_hz": 2,
        "opencv": cv2.__version__,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    cache_dir = output.parent / (output.stem + "-events")
    cache_dir.mkdir(exist_ok=True)
    candidates = raw.get("observed_events", raw.get("events", []))
    if not candidates and not any(key in raw for key in ("observed_events", "events")):
        raise ValueError("Unsupported event artifact")
    if motion_review:
        manifest = json.loads(motion_review.read_text())
        if manifest["source_sha256"] != source_hash:
            raise ValueError("Shot manifest and video differ")
        shots = manifest["shots"]
        shot_indices = {s["id"]: i for i, s in enumerate(shots)}
    else:
        shots, shot_indices = [], {}
    capture = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        raise ValueError("Cannot open source video")
    cal, cfg = make_calibrator()
    track_cache, results = {}, []
    for index, event in enumerate(candidates):
        event_id = event.get("candidate_id", event.get("id"))
        cache_path = cache_dir / f"{index:04}.json"
        if cache_path.exists():
            cached = json.loads(cache_path.read_text())
            if cached["context"] != context or cached["event"]["candidate_id"] != event_id:
                raise ValueError("Aggregate cache context changed; use a new output directory")
            results.append(cached["event"])
            continue
        row = {
            "candidate_id": event_id,
            "event_prediction": event,
            "segments": [],
            "failure_reasons": [],
            "identity_status": "unverified",
            "full_trajectory_validated": False,
        }
        pixel_tracks = []
        split = "observed_track_points" in event
        if split:
            points = event.get("continued_track_points") or event["observed_track_points"]
            groups, reasons = bounded_segments(points)
            row["failure_reasons"].extend(reasons)
            pixel_tracks = [
                {"points": group, "camera_shot_id": "left_split", "colour": event.get("colour")}
                for group in groups
            ]
            row["association_status"] = "detector_track_identity_unverified"
        elif event.get("shot_id") in shot_indices:
            i = shot_indices[event["shot_id"]]
            hypotheses = []
            for shot in shots[i : i + 2]:
                hypotheses.extend(recover_shot_tracks(capture, shot, track_cache))
            hypotheses = [
                t
                for t in hypotheses
                if event.get("colour") is None or t["colour"] == event["colour"]
            ]
            row["motion_hypothesis_count"] = len(hypotheses)
            # Keep evidence; never choose the longest track as a delivered-stone identity.
            row["motion_hypotheses"] = hypotheses
            row["association_status"] = (
                "unique_motion_hypothesis"
                if len(hypotheses) == 1
                else "ambiguous_or_missing_motion"
            )
            if len(hypotheses) == 1:
                groups, reasons = bounded_segments(hypotheses[0]["points"])
                row["failure_reasons"].extend(reasons)
                pixel_tracks = [{**hypotheses[0], "points": group} for group in groups]
            else:
                row["failure_reasons"].append(
                    "stone_identity_ambiguous" if hypotheses else "no_sustained_motion_track"
                )
            row["failure_reasons"].append("no_calibration_reference_for_2022_camera")
        else:
            row["failure_reasons"].append("no_pixel_track_or_shot_manifest")
        for track in pixel_tracks:
            segment = {
                "camera": track["camera_shot_id"],
                "colour": track["colour"],
                "pixel_points": track["points"],
                "geometry_samples": [],
            }
            previous = None
            for point in sample_segment(track["points"]):
                if split:
                    frame = read_frame(capture, point["time_s"])
                    # At a detected cut, keep a gap rather than drawing a joined path.
                    if (
                        previous is not None
                        and scene_cut_evidence(previous[:, :320], frame[:, :320])["hard_cut"]
                    ):
                        remaining = [
                            p for p in segment["pixel_points"] if p["time_s"] >= point["time_s"]
                        ]
                        segment["pixel_points"] = [
                            p for p in segment["pixel_points"] if p["time_s"] < point["time_s"]
                        ]
                        row["segments"].append(segment)
                        segment = {
                            "camera": track["camera_shot_id"],
                            "colour": track["colour"],
                            "pixel_points": remaining,
                            "geometry_samples": [],
                        }
                        row["failure_reasons"].append("camera_cut_breaks_identity")
                    geometry = project_sample(frame, point, cal, cfg)
                    previous = frame
                else:
                    geometry = {
                        "time_s": point["time_s"],
                        "pixel": point["pixel"],
                        "top_view_m": None,
                        "homography_source_pixels_to_local_metres": None,
                        "status": "no_calibration_reference_for_2022_camera",
                    }
                segment["geometry_samples"].append(geometry)
            row["segments"].append(segment)
        row["failure_reasons"] = sorted(set(row["failure_reasons"]))
        cache_path.write_text(json.dumps({"context": context, "event": row}, indent=2) + "\n")
        results.append(row)
        print(f"trajectory {index + 1}/{len(candidates)} {event_id}", flush=True)
    capture.release()
    result = {
        "schema_version": "aggregate-throw-v1",
        "context": context,
        "source_interval_s": raw["source_interval_s"],
        "events": results,
        "summary": summarize(results),
        "limitations": [
            "Image-supported projections are stone-cap ice-plane coordinates; height parallax is uncorrected.",
            "Camera-local coordinates are not joined across camera views; complete trajectories are not inferred.",
            "Registration and ring checks are inference gates, not correctness labels.",
            "2022 cameras have no matching calibration reference; their top-view stage reports failure.",
        ],
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["summary"]), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--motion-review", type=Path)
    parser.add_argument(
        "--base", type=Path, help="Matching frozen aggregate for unchanged departure observations"
    )
    args = parser.parse_args()
    complete(args.video, args.events, args.output, motion_review=args.motion_review, base=args.base)


if __name__ == "__main__":
    main()
