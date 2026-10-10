import cv2
import numpy as np

from prototype.split_house_alignment import paint_reference_overlap, sample_status
from prototype.split_house_reference import right_house_paint_mask
from prototype.scripts.audit_split_house_alignment import unresolved_groups


def painted_frame():
    frame = np.full((360, 640, 3), 235, dtype=np.uint8)
    blue = cv2.cvtColor(np.uint8([[[100, 120, 180]]]), cv2.COLOR_HSV2BGR)[0, 0]
    cv2.ellipse(frame, (480, 160), (135, 14), 0, 0, 360,
                tuple(int(v) for v in blue), -1)
    return frame


def test_paint_alignment_catches_missing_house_without_physical_claim():
    reference_frame = painted_frame()
    reference = right_house_paint_mask(reference_frame)
    assert paint_reference_overlap(reference_frame, reference) == 1
    blank = np.full((360, 640, 3), 235, dtype=np.uint8)
    assert paint_reference_overlap(blank, reference) == 0
    assert sample_status(0) == "house_paint_unresolved_review"
    assert sample_status(1) == "house_paint_aligned_sample"


def test_unresolved_groups_do_not_bridge_supported_runs():
    rows = [{"run_id": "R01", "source_time_s": 2.5,
             "status": "house_paint_unresolved_review", "paint_reference_overlap": .1},
            {"run_id": "R01", "source_time_s": 7.5,
             "status": "house_paint_unresolved_review", "paint_reference_overlap": .2},
            {"run_id": "R02", "source_time_s": 12.5,
             "status": "house_paint_unresolved_review", "paint_reference_overlap": .0}]
    groups = unresolved_groups(rows)
    assert [item["sample_count"] for item in groups] == [2, 1]
