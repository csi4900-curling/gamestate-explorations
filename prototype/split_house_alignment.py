"""Sample-level alignment of right-panel painted house to a run reference."""

import numpy as np

from prototype.split_house_reference import right_house_paint_mask


def paint_reference_overlap(frame, reference_mask):
    mask = right_house_paint_mask(frame).astype(bool)
    reference = np.asarray(reference_mask).astype(bool)
    if reference.shape != mask.shape or reference.sum() < 500:
        raise ValueError("Invalid right-house reference mask")
    return float(np.count_nonzero(mask & reference) / np.count_nonzero(reference))


def sample_status(overlap, *, threshold=0.25):
    if overlap < 0 or overlap > 1 or not 0 < threshold < 1:
        raise ValueError("Invalid paint overlap or threshold")
    return ("house_paint_unresolved_review" if overlap < threshold
            else "house_paint_aligned_sample")
