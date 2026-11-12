"""Panel-aware local-to-rink transforms for left/right split-screen curling.

Each panel's calibrated homography returns view-local metres: origin at that
panel's tee, +x toward image right, +y toward image foreground. The two panels
look from opposite ends, so converting to a shared rink requires the sign of the
panel's hog coordinate. A positive hog coordinate means the far (delivery) end
is in +y; a negative one means it is in -y.

The transform is deliberately data-driven: it reads the signed hog coordinate
recorded by the run instead of assuming left is always the departure camera.
It does not fit calibration, infer a camera role, merge two tracks or establish
physical identity. Lateral handedness is an explicit assumption and is recorded
with every result.
"""

import math

# Nominal 114 ft tee-to-tee distance from Rules-2025, p. 5 (same constant as
# prototype.cross_view). Kept here so the transform is explicit.
TEE_DISTANCE_M = 34.747

# Coarse physical sanity bounds, not calibrated accuracy gates. A curling stone
# released at ~3 m/s and a fast takeout are both far below the speed bound. The
# previous 66 m / 0.4 s representation failures were 100-220 m/s.
MAX_PLAUSIBLE_SPEED_M_S = 10.0
MAX_PLAUSIBLE_GAP_M = 8.0
IMPLAUSIBLE_GAP_M = 30.0


def _sign(value):
    if not math.isfinite(value) or value == 0:
        raise ValueError("Signed hog coordinate must be finite and nonzero")
    return 1.0 if value > 0 else -1.0


def rink_position(local, *, panel, role, hog_y_m, lateral_sign=1.0,
                  tee_distance=TEE_DISTANCE_M):
    """Map one view-local point to a shared rink frame.

    Rink frame: origin at the delivery end's tee, +y toward the receiving end,
    +x chosen by ``lateral_sign`` (default: same image-right direction for both
    panels). ``role`` is the physical role of the *panel* for this throw:
    departure means the panel's tee is the delivery tee; receiving means the
    panel's tee is the receiving tee.
    """
    if panel not in ("left", "right"):
        raise ValueError("panel must be 'left' or 'right'")
    if role not in ("departure", "receiving"):
        raise ValueError("role must be 'departure' or 'receiving'")
    if not math.isfinite(tee_distance) or tee_distance <= 0:
        raise ValueError("tee_distance must be finite and positive")
    if not math.isfinite(lateral_sign) or lateral_sign == 0:
        raise ValueError("lateral_sign must be finite and nonzero")
    point = [float(local[0]), float(local[1])]
    if len(local) != 2 or not all(math.isfinite(v) for v in point):
        raise ValueError("Expected a finite 2D local coordinate")
    s = _sign(float(hog_y_m[panel]))
    x, y = point
    x_rink = lateral_sign * x
    if role == "departure":
        return [x_rink, s * y]
    return [x_rink, tee_distance - s * y]


def handoff_from_rink(departure_rink, receiving_rink, *, departure_time_s,
                      receiving_time_s, max_plausible_speed=MAX_PLAUSIBLE_SPEED_M_S,
                      max_plausible_gap=MAX_PLAUSIBLE_GAP_M,
                      implausible_gap=IMPLAUSIBLE_GAP_M):
    """Describe the unobserved gap between two already-mapped fragments.

    Gap size and implied speed are separate diagnostics. A large gap means the
    cameras did not observe the middle; a high speed means the endpoints are
    inconsistent with stone motion. Neither proves or disproves identity.
    """
    a = [float(departure_rink[0]), float(departure_rink[1])]
    b = [float(receiving_rink[0]), float(receiving_rink[1])]
    dt = float(receiving_time_s) - float(departure_time_s)
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    gap = math.hypot(dx, dy)
    gap_status = ("plausible_gap" if gap <= max_plausible_gap
                  else "large_gap" if gap <= implausible_gap
                  else "implausible_gap")
    if not math.isfinite(dt) or dt <= 0:
        speed = None
        speed_status = "missing_or_nonpositive_time"
        consistency = "missing_or_nonpositive_time"
    else:
        speed = gap / dt
        speed_status = ("plausible_speed" if speed <= max_plausible_speed
                        else "high_speed")
        if gap_status == "implausible_gap":
            consistency = "implausible_gap"
        elif gap_status == "large_gap":
            consistency = "large_gap"
        elif speed_status == "high_speed":
            consistency = "high_speed"
        else:
            consistency = "consistent"
    return {"departure_rink_m": a, "receiving_rink_m": b,
            "gap_m": gap, "lateral_gap_m": abs(dx),
            "longitudinal_gap_m": abs(dy), "gap_s": dt,
            "gap_status": gap_status,
            "implied_speed_m_s": speed,
            "speed_status": speed_status,
            "spatial_consistency": consistency,
            "max_plausible_speed_m_s": max_plausible_speed,
            "max_plausible_gap_m": max_plausible_gap,
            "implausible_gap_m": implausible_gap,
            "interpolated": False, "physical_identity_verified": False}


def handoff_geometry(departure_local, *, departure_panel, receiving_local,
                     receiving_panel, departure_time_s, receiving_time_s,
                     hog_y_m, lateral_sign=1.0, tee_distance=TEE_DISTANCE_M,
                     max_plausible_speed=MAX_PLAUSIBLE_SPEED_M_S,
                     max_plausible_gap=MAX_PLAUSIBLE_GAP_M,
                     implausible_gap=IMPLAUSIBLE_GAP_M):
    """Map two local fragments to the rink and describe their unobserved gap."""
    a = rink_position(departure_local, panel=departure_panel,
                      role="departure", hog_y_m=hog_y_m,
                      lateral_sign=lateral_sign, tee_distance=tee_distance)
    b = rink_position(receiving_local, panel=receiving_panel,
                      role="receiving", hog_y_m=hog_y_m,
                      lateral_sign=lateral_sign, tee_distance=tee_distance)
    return handoff_from_rink(a, b, departure_time_s=departure_time_s,
                             receiving_time_s=receiving_time_s,
                             max_plausible_speed=max_plausible_speed,
                             max_plausible_gap=max_plausible_gap,
                             implausible_gap=implausible_gap)
