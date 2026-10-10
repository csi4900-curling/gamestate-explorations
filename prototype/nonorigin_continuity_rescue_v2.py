"""Phase-aware revision of the source-only non-origin continuity fallback.

The v1 rule and its first-transfer artifacts remain frozen for auditability.
"""

from nonorigin_continuity_rescue import rescue_nonorigin_shots


def rescue_phase_supported_nonorigin_shots(shots, origins, interval_s):
    """Allow the v1 fallback only in shots within the supported delivery phase."""
    filtered = {
        shot_id: {**row, "probability": (row["probability"]
                                        if row.get("phase_supported") is True else -1.0)}
        for shot_id, row in origins.items()
    }
    return rescue_nonorigin_shots(shots, filtered, interval_s)
