"""Combined non-ice context tier for a source-visible right proposal."""


def context_tier(ring_fraction, underpoint_fraction, *, threshold=0.25):
    if ring_fraction is None or underpoint_fraction is None:
        return "context_unavailable_review"
    if ring_fraction > threshold or underpoint_fraction > threshold:
        return "context_cluttered_review"
    return "clear_context_review"
