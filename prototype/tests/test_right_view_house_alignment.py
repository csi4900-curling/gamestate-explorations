import numpy as np
import pytest

from prototype.right_view_house_alignment import alignment_probe, blue_house_mask


def test_alignment_probe_recovers_known_translation():
    first = np.zeros((40, 80), np.uint8)
    first[10:15, 5:45] = 1
    first[21:26, 22:72] = 1
    second = np.roll(first, (2, 3), axis=(0, 1))
    result = alignment_probe(first, second, max_shift_px=5)
    assert result["best_translation_second_to_first_px"] == [-3, -2]
    assert result["best_mask_iou"] == 1.0
    assert not result["zero_translation_is_best"]
    assert not result["full_camera_pose_verified"]


def test_alignment_probe_rejects_empty_mask():
    with pytest.raises(ValueError, match="Empty"):
        alignment_probe(np.zeros((5, 5), np.uint8), np.zeros((5, 5), np.uint8))


def test_blue_house_mask_requires_source_shape():
    with pytest.raises(ValueError, match="640x360"):
        blue_house_mask(np.zeros((20, 20, 3), np.uint8))
