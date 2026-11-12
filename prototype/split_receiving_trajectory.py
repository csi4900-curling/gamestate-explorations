"""Small-stone receiving-view recovery with per-frame house/hog calibration."""

import json
from pathlib import Path
import cv2
import numpy as np
from aggregate_trajectory import summarize
from cache_contract import file_sha256
from camera_geometry import calibrate_sequence
from cross_view import rink_position, truncate_after_stability
from integrated_trajectory import link_segments
from scene_cuts import scene_cut_evidence
from source_specific_house_calibration import fit_source_house
from split_house_ellipse_v2 import fit_house_ellipse
from stone_motion_fallback import stone_cap_candidates, moving_cap_tracks
from vision_core import project

ROOT = Path(__file__).resolve().parents[1]


def incoming_crossing(samples):
    """Require a measured inward hog crossing and sustained approach, not proximity."""
    valid = [p for p in samples if p["top_view_m"] is not None]
    for a, b in zip(valid, valid[1:]):
        ya, yb = a["top_view_m"][1], b["top_view_m"][1]
        if 0 < b["time_s"] - a["time_s"] <= 1.1 and ya >= 6.401 > yb:
            t = a["time_s"] + (6.401 - ya) / (yb - ya) * (b["time_s"] - a["time_s"])
            near = [p for p in valid if abs(p["time_s"] - t) <= 2]
            if len(near) >= 3 and near[0]["top_view_m"][1] - near[-1]["top_view_m"][1] >= 0.5:
                return t
    return None


def complete_receiving(video, base_path, output):
    cv2.setNumThreads(2)
    cv2.setRNGSeed(0)
    base = json.loads(base_path.read_text())
    digest = file_sha256(video)
    if base["context"]["source_sha256"] != digest:
        raise ValueError("Source mismatch")
    files = [
        "prototype/split_receiving_trajectory.py",
        "prototype/split_pipeline.py",
        "prototype/source_specific_house_calibration.py",
        "prototype/split_house_ellipse_v2.py",
        "prototype/split_house_reference.py",
        "prototype/house_affine_transfer_audit.py",
        "prototype/camera_geometry.py",
        "prototype/automatic_house_calibration.py",
        "prototype/rectification_core.py",
        "prototype/vision_core.py",
        "prototype/stone_motion_fallback.py",
        "prototype/scene_cuts.py",
        "prototype/cross_view.py",
        "prototype/integrated_trajectory.py",
        "prototype/aggregate_trajectory.py",
        "prototype/rectification/calibration.json",
        "prototype/vision/frames/06495.jpg",
    ]
    context = {
        "source_sha256": digest,
        "events_sha256": base["context"]["events_sha256"],
        "upstream_sha256": file_sha256(base_path),
        "code_sha256": {f: file_sha256(ROOT / f) for f in files},
        "tracking_hz": 2,
        "opencv": cv2.__version__,
    }
    cap = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened() or fps <= 0:
        raise ValueError("Cannot open source")
    reference = cv2.resize(cv2.imread(str(ROOT / "prototype/vision/frames/06495.jpg")), (640, 360))
    ref_ellipse = fit_house_ellipse(reference)
    ref_H = json.loads((ROOT / "prototype/rectification/calibration.json").read_text())["right"][
        "refined_H"
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    cache = output.parent / "receiving-events"
    cache.mkdir(exist_ok=True)
    results = []
    for index, original in enumerate(base["events"]):
        cached = cache / f"{index:04}.json"
        if cached.exists():
            saved = json.loads(cached.read_text())
            if saved["context"] != context:
                raise ValueError("Receiving context changed; use fresh output")
            results.append(saved["event"])
            continue
        event = json.loads(json.dumps(original))
        prediction = event["event_prediction"]
        points = prediction.get("observed_track_points", [])
        if not points:
            results.append(event)
            cached.write_text(json.dumps({"context": context, "event": event}) + "\n")
            continue
        event["segments"] = [s for s in event["segments"] if s["camera"] == "left_split"]
        event["failure_reasons"] = [
            r
            for r in event["failure_reasons"]
            if r != "cross_view_identity_unresolved" and not r.endswith(":right_split")
        ]
        colour = prediction["colour"]
        start = points[0]["time_s"]
        end = min(start + 40, base["source_interval_s"][1])
        first = int(np.ceil(start * fps))
        last = int(np.ceil(end * fps))
        step = max(1, round(fps / 2))
        cap.set(cv2.CAP_PROP_POS_FRAMES, first)
        observations = []
        frames = {}
        cuts = []
        previous = None
        for i in range(first, last):
            if not cap.grab():
                raise RuntimeError(f"Decode failed at {i}")
            if (i - first) % step:
                continue
            ok, frame = cap.retrieve()
            if not ok:
                raise RuntimeError(f"Retrieve failed at {i}")
            frame = cv2.resize(frame, (640, 360))
            t = round(i / fps, 3)
            crop = frame[110:360, 320:640]
            if previous is not None and scene_cut_evidence(previous, crop)["hard_cut"]:
                cuts.append(t)
            previous = crop
            frames[t] = frame
            caps = []
            for p in stone_cap_candidates(
                crop, colour, allow_bright_body=True, allow_large_caps=True
            ):
                x, y = p["pixel"]
                bx, by, bw, bh = p["bbox"]
                caps.append(
                    {
                        **p,
                        "pixel": [320 + x * 0.5, 110 + y * 250 / 360],
                        "bbox": [320 + bx * 0.5, 110 + by * 250 / 360, bw * 0.5, bh * 250 / 360],
                        "channel": "panel_scaled_cap",
                    }
                )
            observations.append((t, caps))
        tracks = moving_cap_tracks(observations, max_gap_s=1.1, max_step_px=130, cut_times_s=cuts)
        # Geometry is only needed at observed track samples; the house fit uses its own held-out paint checks.
        times = sorted({p["time_s"] for track in tracks for p in track["points"]})
        initial = {}
        for t in times:
            ellipse = fit_house_ellipse(frames[t])
            initial[t] = (
                fit_source_house(frames[t], ellipse, ref_H, ref_ellipse)
                if ellipse and ref_ellipse
                else (None, {"status": "no_receiving_house_ellipse"})
            )
        geometry = calibrate_sequence(
            {t: frames[t] for t in times}, (320, 70, 640, 360), cuts, initial=initial
        )
        eligible = []
        hypotheses = []
        for track in tracks:
            samples = []
            widths = []
            for p in track["points"]:
                H, diag = geometry[p["time_s"]]
                g = {
                    "time_s": p["time_s"],
                    "pixel": p["pixel"],
                    "top_view_m": None,
                    "rink_position_m": None,
                    "homography_source_pixels_to_local_metres": None,
                    "status": diag["status"],
                    "calibration": diag,
                }
                if H is not None:
                    try:
                        xy = project(H, [p["pixel"]])[0]
                        x, y, w, h = p["bbox"]
                        width = float(
                            np.linalg.norm(
                                np.diff(project(H, [[x, y + h / 2], [x + w, y + h / 2]]), axis=0)
                            )
                        )
                        if abs(xy[0]) <= 2.375 and -2 <= xy[1] <= 32 and 0.04 <= width <= 0.55:
                            widths.append(width)
                            g.update(
                                top_view_m=xy.tolist(),
                                rink_position_m=rink_position(xy, "receiving"),
                                homography_source_pixels_to_local_metres=H.tolist(),
                                status="image_supported_ice_plane_projection",
                            )
                        else:
                            g["status"] = "outside_rink_or_stone_scale"
                    except ValueError:
                        g["status"] = "invalid_planar_projection"
                samples.append(g)
            crossing = incoming_crossing(samples)
            record = {
                "camera": "right_split",
                "role": "receiving",
                "colour": colour,
                "pixel_points": track["points"],
                "geometry_samples": samples,
                "receiving_hog_crossing_s": crossing,
                "associated": False,
                "orientation_status": "source_family_hog_line_orientation",
                "association_evidence": {
                    "observed_inward_hog_crossing": crossing is not None,
                    "median_cap_width_m": float(np.median(widths)) if widths else None,
                },
                "camera_cut_times_s": cuts,
            }
            hypotheses.append(record)
            if crossing is not None:
                eligible.append(record)
        event["receiving_hypotheses"] = hypotheses
        if len(eligible) == 1:
            chosen = eligible[0]
            chosen["associated"] = True
            pts, stop = truncate_after_stability(chosen["pixel_points"])
            # A stationary pre-approach prefix cannot terminate a later incoming track.
            if stop and stop["time_s"] < chosen["receiving_hog_crossing_s"]:
                pts = chosen["pixel_points"]
                stop = None
            chosen = {
                **chosen,
                "pixel_points": pts,
                "geometry_samples": [
                    g for g in chosen["geometry_samples"] if g["time_s"] <= pts[-1]["time_s"]
                ],
                "observed_stop": stop,
            }
            event["segments"].append(chosen)
        else:
            event["failure_reasons"].append(
                "ambiguous_incoming_tracks" if eligible else "no_observed_incoming_hog_crossing"
            )
        for n, s in enumerate(event["segments"]):
            s["segment_id"] = f"{event['candidate_id']}:{n}"
        event["cross_view_links"] = link_segments(event["segments"])
        if not event["cross_view_links"]:
            event["failure_reasons"].append("cross_view_identity_unresolved")
        cached.write_text(json.dumps({"context": context, "event": event}) + "\n")
        results.append(event)
        print(
            f"receiving {index + 1}/{len(base['events'])} {event['candidate_id']}: {len(eligible)} incoming candidates, {len(event['cross_view_links'])} links",
            flush=True,
        )
    cap.release()
    # Overlapping event windows must not claim the same observed incoming crossing.
    claims = [
        (e, s)
        for e in results
        for s in e["segments"]
        if s.get("receiving_hog_crossing_s") is not None
    ]
    rejected = set()
    for i, (a, x) in enumerate(claims):
        for b, y in claims[i + 1 :]:
            if (
                a["candidate_id"] != b["candidate_id"]
                and x["colour"] == y["colour"]
                and abs(x["receiving_hog_crossing_s"] - y["receiving_hog_crossing_s"]) < 2
            ):
                rejected.update([x["segment_id"], y["segment_id"]])
    for e in results:
        e["unassigned_segments"] = e.get("unassigned_segments", []) + [
            s for s in e["segments"] if s["segment_id"] in rejected
        ]
        if any(s["segment_id"] in rejected for s in e["segments"]):
            e["failure_reasons"].append("incoming_crossing_claimed_by_multiple_events")
        e["segments"] = [s for s in e["segments"] if s["segment_id"] not in rejected]
        e["cross_view_links"] = link_segments(e["segments"])
        e["failure_reasons"] = sorted(set(e["failure_reasons"]))
    summary = summarize(results)
    summary["events_with_cross_view_link"] = sum(bool(e["cross_view_links"]) for e in results)
    result = {
        **base,
        "schema_version": "aggregate-throw-v4",
        "context": context,
        "events": results,
        "summary": summary,
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    return result
