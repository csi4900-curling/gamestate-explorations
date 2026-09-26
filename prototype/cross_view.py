"""Explicit local-to-rink transforms and conservative passage association."""

import numpy as np

TEE_DISTANCE_M = 34.747  # Nominal 114 ft diagram, Rules-2025.pdf, page 5.
HOG_FROM_TEE_M = 6.401


def rink_position(local, view, tee_distance=TEE_DISTANCE_M):
    if view not in ("departure", "receiving"):
        raise ValueError("Unknown camera role")
    point = np.asarray(local, float)
    if point.shape != (2,) or not np.isfinite(point).all():
        raise ValueError("Expected a finite 2D coordinate")
    if not np.isfinite(tee_distance) or tee_distance <= 0:
        raise ValueError("Invalid tee distance")
    x, y = point
    return [float(x), float(-y + (tee_distance if view == "receiving" else 0))]


def validate_times(points, key="time_s"):
    times = [p[key] for p in points]
    if not np.isfinite(times).all() or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("Observation times must be finite and strictly increasing")


def arrival_candidates(segment):
    event = segment["event"]
    gate = event["crossing_time_s"]
    boundary = segment["review_interval_s"][1]
    tracks = {}
    if not np.isfinite([gate, boundary]).all() or boundary <= gate:
        raise ValueError("Invalid event interval")
    validate_times(segment["timeline"]["records"], "source_time_s")
    for row in segment["timeline"]["records"]:
        t = row["source_time_s"]
        if t >= boundary:
            continue
        for s in row["views"]["right"]["stones"]:
            if s["colour"] == event["colour"]:
                tracks.setdefault(s["track_id"], []).append(
                    {"time_s": t, "pixel": s["pixel_center"], "local_m": s["ground_position_m"]}
                )
    candidates = []
    rejected = []
    for tid, pts in tracks.items():
        if not gate < pts[0]["time_s"] < min(gate + 35, boundary):
            continue
        metric = [p for p in pts if p["local_m"] is not None]
        cross = None
        for p in metric:
            rink_position(p["local_m"], "receiving")
        if len(metric) < 3:
            continue
        # Must actually be observed approaching and crossing the receiving hog line.
        for a, b in zip(metric, metric[1:]):
            ya, yb = a["local_m"][1], b["local_m"][1]
            if 0 < b["time_s"] - a["time_s"] <= 1.01 and ya >= HOG_FROM_TEE_M > yb:
                alpha = (ya - HOG_FROM_TEE_M) / (ya - yb)
                cross = a["time_s"] + alpha * (b["time_s"] - a["time_s"])
                break
        if cross is None:
            rejected.append(
                {"track_id": tid, "reason": "No observed inward receiving hog-line crossing."}
            )
            continue
        near = [p for p in metric if abs(p["time_s"] - cross) <= 2]
        if len(near) < 3 or near[0]["local_m"][1] - near[-1]["local_m"][1] < 0.5:
            rejected.append({"track_id": tid, "reason": "Insufficient sustained incoming motion."})
            continue
        candidates.append(
            {
                "track_id": tid,
                "first_observed_s": pts[0]["time_s"],
                "hog_crossing_s": cross,
                "track": pts,
                "association_basis": "Same colour, new track within 35 seconds, observed inward crossing of receiving hog line with sustained motion.",
            }
        )
    return candidates, rejected


def truncate_after_stability(points):
    """End the displayed delivered-stone episode; keep later raw observations separately."""
    validate_times(points)
    for p in points:
        pixel = np.asarray(p["pixel"], float)
        if pixel.shape != (2,) or not np.isfinite(pixel).all():
            raise ValueError("Invalid image position")
    for i, p in enumerate(points):
        window = points[max(0, i - 4) : i + 1]
        if len(window) < 5 or abs(window[-1]["time_s"] - window[0]["time_s"] - 2) > 0.01:
            continue
        if any(b["time_s"] - a["time_s"] > 0.51 for a, b in zip(window, window[1:])):
            continue
        xy = np.array([q["pixel"] for q in window])
        spread = np.max(np.linalg.norm(xy - np.median(xy, axis=0), axis=1))
        if spread <= 3 and abs(xy[-1, 1] - xy[0, 1]) <= 2:
            return points[: i + 1], {
                "time_s": p["time_s"],
                "status": "delivered_stone_visually_stable_candidate",
                "physical_end_verified": False,
            }
    return points, None


def connect(segment, departure):
    if departure.get("event_id", segment["event"]["id"]) != segment["event"]["id"]:
        raise ValueError("Departure event ID does not match receiving segment")
    validate_times(departure["records"])
    candidates, rejected = arrival_candidates(segment)
    dep = [
        dict(r, world_m=rink_position(r["position_local_m"], "departure"))
        for r in departure["records"]
        if r["position_local_m"] is not None
    ]
    valid = []
    for c in candidates:
        arr = [
            dict(p, world_m=rink_position(p["local_m"], "receiving"))
            for p in c["track"]
            if p["local_m"] is not None
        ]
        if not dep or not arr:
            continue
        a, b = dep[-1], arr[0]
        dt = b["time_s"] - a["time_s"]
        dy = b["world_m"][1] - a["world_m"][1]
        if dt <= 0 or dy <= 0:
            rejected.append(
                {
                    "track_id": c["track_id"],
                    "reason": "No forward, time-ordered connection in shared rink coordinates.",
                }
            )
            continue
        valid.append(
            dict(
                c,
                world_track=arr,
                gap={
                    "start_s": a["time_s"],
                    "end_s": b["time_s"],
                    "duration_s": dt,
                    "longitudinal_distance_m": dy,
                    "mean_longitudinal_speed_m_s": dy / dt,
                    "lateral_difference_m": b["world_m"][0] - a["world_m"][0],
                    "interpolated": False,
                },
            )
        )
    chosen = valid[0] if len(valid) == 1 else None
    arrival, stop = truncate_after_stability(chosen["world_track"]) if chosen else ([], None)
    return {
        "id": segment["event"]["id"],
        "colour": segment["event"]["colour"],
        "gate_time_s": segment["event"]["crossing_time_s"],
        "departure": dep,
        "departure_samples": len(departure["records"]),
        "candidate_count": len(valid),
        "status": "provisional_link" if chosen else "unresolved",
        "arrival": arrival,
        "raw_arrival": chosen["world_track"] if chosen else [],
        "arrival_display_stop": stop,
        "receiving_track_id": chosen["track_id"] if chosen else None,
        "receiving_hog_crossing_s": chosen["hog_crossing_s"] if chosen else None,
        "gap": chosen["gap"] if chosen else None,
        "rejected_candidates": rejected,
        "independently_verified_identity": False,
        "physical_accuracy_measured": False,
    }
