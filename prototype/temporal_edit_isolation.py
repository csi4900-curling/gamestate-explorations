"""Describe whether a frame-change peak is isolated in time."""


def edit_isolation(left, center, right, *, min_gray_ratio=2.0,
                   min_hist_ratio=2.0):
    """Compare a proposed boundary with its immediate neighboring frame pairs."""
    for row in (left, center, right):
        if row["gray_change"] < 0 or row["hist_distance"] < 0:
            raise ValueError("Frame-change metrics must be nonnegative")
    gray_ratio = center["gray_change"] / max(
        left["gray_change"], right["gray_change"], 1.0)
    hist_ratio = center["hist_distance"] / max(
        left["hist_distance"], right["hist_distance"], 0.001)
    return {
        "gray_isolation_ratio": round(gray_ratio, 3),
        "hist_isolation_ratio": round(hist_ratio, 3),
        "isolated_spike": gray_ratio >= min_gray_ratio and
        hist_ratio >= min_hist_ratio,
    }
