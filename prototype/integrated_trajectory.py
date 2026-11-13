"""Video-derived camera segments, geometry, association and event trajectories."""

import json
from functools import lru_cache
from pathlib import Path
import cv2
import numpy as np
from automatic_house_calibration import calibrate_house
from aggregate_trajectory import bounded_segments, sample_segment, summarize
from cache_contract import file_sha256
from cross_view import rink_position
from scene_cuts import scene_cut_evidence
from stone_motion_fallback import moving_cap_tracks, stone_cap_candidates
from stone_patch_detector import detect_stones, load_model
from vision_core import project

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / "validation/curlobserver-learned-probe/model-v1/model.npz"


def orient_image_aligned_samples(samples, role):
    """Rotate image-right/down local axes into an upward-travel rink display.

    The rink canvas reverses Y. Therefore the local-to-rink transform must
    reverse exactly one axis, not preserve both (which reflects the display).
    Motion chooses the provisional travel direction; it does not establish
    physical camera identity or an absolute surveyed rink orientation.
    """
    for point in samples:
        point["rink_position_m"] = None
    valid = [p for p in samples if p["top_view_m"] is not None]
    if role not in ("departure", "receiving") or len(valid) < 2:
        return "unresolved"
    delta = np.subtract(valid[-1]["top_view_m"], valid[0]["top_view_m"])
    if abs(delta[1]) <= max(0.25, abs(delta[0])):
        return "unresolved"
    direction = 1 if delta[1] > 0 else -1
    for point in valid:
        x, y = point["top_view_m"]
        point["rink_position_m"] = [
            -direction * x,
            direction * y + (34.747 if role == "receiving" else 0),
        ]
    return "provisional_rotation_from_camera_role_and_observed_motion"


def geometry_sample(frame, point, region, role, cache=None):
    key = (point["time_s"], tuple(region))
    if cache is not None and key in cache:
        H, diagnostic = cache[key]
    else:
        H, diagnostic = calibrate_house(frame, region)
        if cache is not None:
            cache[key] = (H, diagnostic)
    result = {
        "time_s": point["time_s"],
        "pixel": point["pixel"],
        "top_view_m": None,
        "homography_source_pixels_to_local_metres": None,
        "status": diagnostic["status"],
        "calibration": diagnostic,
        "rink_position_m": None,
    }
    if H is None:
        return result
    try:
        xy = project(H, [point["pixel"]])[0]
        if abs(xy[0]) > 2.375 or abs(xy[1]) > 32:
            result["status"] = "outside_nominal_rink_bounds"
            return result
        # Rink axes require a known camera role; local coordinates remain available.
        result.update(
            top_view_m=xy.tolist(),
            homography_source_pixels_to_local_metres=H.tolist(),
            status="image_supported_ice_plane_projection",
        )
        result["rink_position_m"] = None
    except ValueError:
        result["status"] = "invalid_planar_projection"
    return result


def scan_window(capture, start, end, region, model):
    """Both detector channels, shot-safe tracks, and actual per-frame coordinates."""
    fps = capture.get(cv2.CAP_PROP_FPS)
    step = max(1, round(fps / 2))
    first = int(np.ceil(start * fps))
    last = int(np.ceil(end * fps))
    capture.set(cv2.CAP_PROP_POS_FRAMES, first)
    observations = {"red": [], "yellow": []}
    cuts = []
    previous = None
    for i in range(first, last):
        if not capture.grab():
            raise RuntimeError(f"Cannot decode frame {i}")
        if (i - first) % step:
            continue
        ok, frame = capture.retrieve()
        if not ok:
            raise RuntimeError(f"Cannot retrieve frame {i}")
        frame = cv2.resize(frame, (640, 360))
        t = round(i / fps, 3)
        x0, y0, x1, y1 = region
        crop = frame[y0:y1, x0:x1]
        if previous is not None and scene_cut_evidence(previous, crop)["hard_cut"]:
            cuts.append(t)
        previous = crop
        # Existing learned weights and threshold; no event labels used.
        boxes = detect_stones(frame, model)
        for colour in observations:
            caps = stone_cap_candidates(
                frame, colour, allow_bright_body=True, allow_large_caps=True
            )
            proposals = []
            for cap in caps:
                x, y = cap["pixel"]
                if not (x0 <= x < x1 and y0 <= y < y1):
                    continue
                support = [
                    b
                    for b in boxes
                    if b["colour"] == colour
                    and b["bbox"][0] <= x <= b["bbox"][0] + b["bbox"][2]
                    and b["bbox"][1] <= y <= b["bbox"][1] + b["bbox"][3]
                ]
                proposals.append({**cap, "channels": ["cap", "learned"] if support else ["cap"]})
            for box in boxes:
                if box["colour"] != colour:
                    continue
                x, y, w, h = box["bbox"]
                pixel = [x + w / 2, y + h / 2]
                if not (x0 <= pixel[0] < x1 and y0 <= pixel[1] < y1):
                    continue
                if any(
                    x <= p["pixel"][0] <= x + w and y <= p["pixel"][1] <= y + h for p in proposals
                ):
                    continue
                proposals.append(
                    {
                        "pixel": pixel,
                        "bbox": box["bbox"],
                        "confidence": box["confidence"],
                        "channels": ["learned"],
                    }
                )
            observations[colour].append((t, proposals))
    tracks = []
    for colour, samples in observations.items():
        for track in moving_cap_tracks(samples, max_gap_s=1.0, max_step_px=130, cut_times_s=cuts):
            tracks.append({**track, "colour": colour})
    return tracks, cuts


def assess_track(track, samples):
    """Stone identity evidence from both appearance and local physical scale."""
    points = track["points"]
    learned = sum("learned" in p.get("channels", []) for p in points) / len(points)
    valid = []
    widths = []
    for g in samples:
        if g["top_view_m"] is None:
            continue
        p = min(points, key=lambda p: abs(p["time_s"] - g["time_s"]))
        if "bbox" in p:
            x, y, w, h = p["bbox"]
            H = np.asarray(g["homography_source_pixels_to_local_metres"])
            try:
                widths.append(
                    float(
                        np.linalg.norm(
                            np.diff(project(H, [[x, y + h / 2], [x + w, y + h / 2]]), axis=0)
                        )
                    )
                )
            except ValueError:
                pass
        valid.append(g)
    moving = False
    moving_pairs = 0
    for a, b in zip(valid, valid[1:]):
        dt = b["time_s"] - a["time_s"]
        if (
            0 < dt <= 1.6
            and 0.03 < np.linalg.norm(np.subtract(b["top_view_m"], a["top_view_m"])) / dt < 5
        ):
            moving_pairs += 1
    if len(valid) >= 3:
        displacement = np.linalg.norm(np.subtract(valid[-1]["top_view_m"], valid[0]["top_view_m"]))
        moving = moving_pairs >= 2 and displacement >= 0.5
    scale_ok = bool(widths and 0.04 <= np.median(widths) <= 0.55)
    return {
        "learned_support_fraction": learned,
        "median_projected_width_m": float(np.median(widths)) if widths else None,
        "physical_scale_supported": scale_ok,
        "calibrated_motion_supported": bool(moving),
        "eligible": bool(learned >= 0.5 and scale_ok and moving),
    }


def link_segments(segments):
    """Unique, forward, colour-compatible linkage; never interpolate hidden travel."""
    dep = [s for s in segments if s.get("role") == "departure" and s.get("associated")]
    arr = [s for s in segments if s.get("role") == "receiving" and s.get("associated")]
    links = []
    for a in dep:
        aa = [p for p in a["geometry_samples"] if p.get("rink_position_m") is not None]
        possible = []
        for b in arr:
            if a["colour"] != b["colour"]:
                continue
            bb = [p for p in b["geometry_samples"] if p.get("rink_position_m") is not None]
            if not aa or not bb:
                continue
            receiving_hog = 34.747 - 6.401
            if not any(
                0 < q["time_s"] - p["time_s"] <= 1.6
                and p["rink_position_m"][1] <= receiving_hog < q["rink_position_m"][1]
                for p, q in zip(bb, bb[1:])
            ):
                continue
            first = next((p for p in bb if p["time_s"] >= aa[-1]["time_s"]), None)
            if first is None:
                continue
            dt = first["time_s"] - aa[-1]["time_s"]
            delta = np.subtract(first["rink_position_m"], aa[-1]["rink_position_m"])
            if 0 <= dt <= 35 and 0 <= delta[1] <= max(1.5, 5 * dt) and abs(delta[0]) <= 2:
                possible.append(
                    {
                        "departure_segment": a["segment_id"],
                        "receiving_segment": b["segment_id"],
                        "gap_s": dt,
                        "displacement_m": delta.tolist(),
                        "interpolated": False,
                        "identity_status": "provisional_geometry_and_colour_link",
                    }
                )
        if len(possible) == 1:
            links.extend(possible)
    return links


def reject_reused_tracks(events):
    """A source track cannot silently be assigned to two distinct event candidates."""
    owners = {}
    for event in events:
        for segment in event["segments"]:
            if segment.get("camera") == "left_split":
                continue
            points = segment["pixel_points"]
            signature = (
                segment["camera"],
                segment["colour"],
                tuple((p["time_s"], tuple(p["pixel"])) for p in points),
            )
            owners.setdefault(signature, []).append((event, segment))
    rejected = set()
    for rows in owners.values():
        if len({e["candidate_id"] for e, _ in rows}) > 1:
            for event, segment in rows:
                rejected.add(segment["segment_id"])
                event["failure_reasons"].append("track_claimed_by_multiple_events")
                event.setdefault("unassigned_segments", []).append(segment)
    for event in events:
        event["segments"] = [s for s in event["segments"] if s["segment_id"] not in rejected]
        event["cross_view_links"] = link_segments(event["segments"])
        event["failure_reasons"] = sorted(set(event["failure_reasons"]))


def complete_integrated(
    video, events_path, output, *, motion_review=None, base=None, learned_model=DEFAULT_MODEL
):
    cv2.setNumThreads(2)
    cv2.setRNGSeed(0)
    raw = json.loads(events_path.read_text())
    digest = file_sha256(video)
    if raw["source_sha256"] != digest:
        raise ValueError("Event/source fingerprint mismatch")
    model = load_model(learned_model)
    code_files = [
        "integrated_trajectory.py",
        "automatic_house_calibration.py",
        "aggregate_trajectory.py",
        "cross_view.py",
        "stone_patch_detector.py",
        "stone_motion_fallback.py",
        "rectification_core.py",
        "vision_core.py",
        "scene_cuts.py",
    ]
    context = {
        "source_sha256": digest,
        "events_sha256": file_sha256(events_path),
        "model_sha256": file_sha256(learned_model),
        "code_sha256": {f: file_sha256(ROOT / "prototype" / f) for f in code_files},
        "motion_review_sha256": file_sha256(motion_review) if motion_review else None,
        "base_sha256": file_sha256(base) if base else None,
        "opencv": cv2.__version__,
        "tracking_sample_rate_hz": 2,
        "geometry_sample_rate_hz": 1,
    }
    embedded_manifests = {
        e["motion_review_path"]
        for e in raw.get("observed_events", raw.get("events", []))
        if e.get("motion_review_path")
    }
    context["embedded_manifests_sha256"] = {
        p: file_sha256(Path(p)) for p in sorted(embedded_manifests)
    }
    context["reference_sha256"] = {
        f: file_sha256(ROOT / f)
        for f in (
            "prototype/scripts/complete_throw_trajectories.py",
            "prototype/vision/annotations/calibration.json",
            "prototype/rectification/calibration.json",
            "prototype/vision/frames/00750.jpg",
        )
    }
    old = {}
    if base:
        seed = json.loads(base.read_text())
        if (
            seed["context"]["source_sha256"] != digest
            or seed["context"]["events_sha256"] != context["events_sha256"]
        ):
            raise ValueError("Base predictions do not match input")
        old = {e["candidate_id"]: e for e in seed["events"]}
    manifest = json.loads(motion_review.read_text()) if motion_review else None
    if manifest and manifest["source_sha256"] != digest:
        raise ValueError("Shot source mismatch")
    shots = manifest["shots"] if manifest else []
    indices = {s["id"]: i for i, s in enumerate(shots)}
    events = raw.get("observed_events", raw.get("events", []))
    results = []
    output.parent.mkdir(parents=True, exist_ok=True)
    cache = output.parent / (output.stem + "-events")
    cache.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise ValueError("Cannot open video")
    from scripts.complete_throw_trajectories import make_calibrator, project_sample, read_frame

    @lru_cache(maxsize=128)
    def get_frame(t):
        return read_frame(cap, t)

    geometry_cache = {}
    left_cal, left_cfg = make_calibrator()
    windows = {}
    for index, event in enumerate(events):
        key = event.get("id", event.get("candidate_id"))
        cached = cache / f"{index:04}.json"
        if cached.exists():
            saved = json.loads(cached.read_text())
            if saved["context"] != context:
                raise ValueError("Changed inference context; use fresh output")
            results.append(saved["event"])
            continue
        row = {
            "candidate_id": key,
            "event_prediction": event,
            "segments": [],
            "failure_reasons": [],
            "identity_status": "unverified",
            "full_trajectory_validated": False,
            "motion_hypotheses": [],
        }
        if event.get("motion_review_path"):
            embedded = json.loads(Path(event["motion_review_path"]).read_text())
            if embedded["source_sha256"] != digest:
                raise ValueError("Embedded shot manifest source mismatch")
            shots = embedded["shots"]
            indices = {s["id"]: i for i, s in enumerate(shots)}
        split = "observed_track_points" in event
        jobs = []
        if split:
            points = event.get("continued_track_points") or event["observed_track_points"]
            groups, reasons = bounded_segments(points)
            row["failure_reasons"] += reasons
            if key in old:
                for s in old[key]["segments"]:
                    s = json.loads(json.dumps(s))
                    s.update(role="departure", associated=True)
                    for g in s["geometry_samples"]:
                        g["rink_position_m"] = (
                            rink_position(g["top_view_m"], "departure")
                            if g["top_view_m"] is not None
                            else None
                        )
                    row["segments"].append(s)
            else:
                for group in groups:
                    gs = [
                        project_sample(get_frame(p["time_s"]), p, left_cal, left_cfg)
                        for p in sample_segment(group)
                    ]
                    for g in gs:
                        g["rink_position_m"] = (
                            rink_position(g["top_view_m"], "departure")
                            if g["top_view_m"] is not None
                            else None
                        )
                    row["segments"].append(
                        {
                            "camera": "left_split",
                            "role": "departure",
                            "associated": True,
                            "colour": event.get("colour"),
                            "pixel_points": group,
                            "geometry_samples": gs,
                        }
                    )
            if points:
                start = points[0]["time_s"]
                end = min(start + 40, raw["source_interval_s"][1])
                jobs = [("right_split", start, end, (320, 70, 640, 360), "receiving")]
        elif event.get("shot_id") in indices:
            i = indices[event["shot_id"]]
            for j, shot in enumerate(shots[i : i + 2]):
                start, end = shot["interval_s"]
                role = (
                    ("departure" if j == 0 else "receiving")
                    if event.get("evidence_class") == "origin_view_candidate"
                    else "unknown"
                )
                jobs.append((shot["id"], start, end, (0, 70, 640, 360), role))
        else:
            row["failure_reasons"].append("no_track_or_camera_manifest")
        for camera, start, end, region, role in jobs:
            window_key = (camera, start, end)
            if window_key not in windows:
                tracks, cuts = scan_window(cap, start, end, region, model)
                windows[window_key] = (tracks, cuts)
            tracks, cuts = windows[window_key]
            hypotheses = []
            for track in tracks:
                if event.get("colour") and track["colour"] != event["colour"]:
                    continue
                groups, reasons = bounded_segments(track["points"], max_duration_s=60)
                for group in groups:
                    if len(group) < 4:
                        continue
                    samples = [
                        geometry_sample(get_frame(p["time_s"]), p, region, role, geometry_cache)
                        for p in sample_segment(group, hz=1)
                    ]
                    for g in samples:
                        p = min(group, key=lambda p: abs(p["time_s"] - g["time_s"]))
                        if "learned" not in p.get("channels", []):
                            g.update(
                                top_view_m=None,
                                homography_source_pixels_to_local_metres=None,
                                rink_position_m=None,
                                status="stone_appearance_not_corroborated",
                            )
                    orientation = orient_image_aligned_samples(samples, role)
                    evidence = assess_track({**track, "points": group}, samples)
                    hypotheses.append(
                        {
                            "camera": camera,
                            "role": role,
                            "colour": track["colour"],
                            "pixel_points": group,
                            "geometry_samples": samples,
                            "association_evidence": evidence,
                            "orientation_status": orientation,
                            "camera_cut_times_s": cuts,
                        }
                    )
            eligible = [h for h in hypotheses if h["association_evidence"]["eligible"]]
            # Uniqueness is within each shot, not across physically different views.
            for h in hypotheses:
                h["associated"] = len(eligible) == 1 and h is eligible[0]
                row["motion_hypotheses"].append(h)
                if h["associated"]:
                    supported_points = [
                        p for p in h["pixel_points"] if "learned" in p.get("channels", [])
                    ]
                    groups, _ = bounded_segments(supported_points, max_duration_s=60, max_gap_s=1.1)
                    for group in groups:
                        if len(group) < 2:
                            continue
                        start_t, end_t = group[0]["time_s"], group[-1]["time_s"]
                        row["segments"].append(
                            {
                                **h,
                                "pixel_points": group,
                                "geometry_samples": [
                                    g
                                    for g in h["geometry_samples"]
                                    if start_t <= g["time_s"] <= end_t
                                ],
                            }
                        )
            if len(eligible) > 1:
                row["failure_reasons"].append(f"ambiguous_stone_identity:{camera}")
            elif not eligible:
                row["failure_reasons"].append(f"no_supported_stone_track:{camera}")
        for n, s in enumerate(row["segments"]):
            s["segment_id"] = f"{key}:{n}"
        row["cross_view_links"] = link_segments(row["segments"])
        if not row["cross_view_links"]:
            row["failure_reasons"].append("cross_view_identity_unresolved")
        row["failure_reasons"] = sorted(set(row["failure_reasons"]))
        cached.write_text(json.dumps({"context": context, "event": row}) + "\n")
        results.append(row)
        print(
            f"integrated {index + 1}/{len(events)} {key}: {len(row['segments'])} segments, {len(row['cross_view_links'])} links",
            flush=True,
        )
    cap.release()
    reject_reused_tracks(results)
    result = {
        "schema_version": "aggregate-throw-v2",
        "context": context,
        "source_interval_s": raw["source_interval_s"],
        "events": results,
        "summary": summarize(results),
        "limitations": [
            "Image-aligned automatic house coordinates do not by themselves establish canonical rink orientation.",
            "Provisional associations retain occlusion/camera gaps; coordinates are cap projections onto ice.",
        ],
    }
    result["summary"]["events_with_cross_view_link"] = sum(
        bool(e["cross_view_links"]) for e in results
    )
    output.write_text(json.dumps(result, indent=2) + "\n")
    return result
