"""Image-relative house fitting must abstain on missing or unstable paint."""

import cv2
import numpy as np

from split_house_ellipse_v2 import fit_house_ellipse, normalized_cap_image_xy, stable_house_ellipse


def synthetic(center):
    frame = np.full((360, 640, 3), 245, dtype=np.uint8)
    cv2.ellipse(frame, center, (132, 15), 0, 0, 360, (210, 130, 30), 7)
    return frame


def test_fits_both_split_house_vertical_positions():
    for center in ((485, 182), (492, 153)):
        result = fit_house_ellipse(synthetic(center))
        assert result is not None
        assert abs(result["center_px"][0] - center[0]) < 3
        assert abs(result["center_px"][1] - center[1]) < 3


def test_three_sample_stability_and_image_only_coordinates():
    samples = [fit_house_ellipse(synthetic((485 + delta, 182))) for delta in (0, 1, -1)]
    stable, status = stable_house_ellipse(samples)
    assert status == "stable_image_paint_ellipse"
    assert abs(normalized_cap_image_xy(stable, [485, 182])[0]) < 0.01
    samples[2] = fit_house_ellipse(synthetic((500, 182)))
    assert stable_house_ellipse(samples)[1] == "abstain_house_ellipse_changes_across_samples"


def test_missing_paint_abstains():
    blank = np.full((360, 640, 3), 245, dtype=np.uint8)
    assert fit_house_ellipse(blank) is None
    assert stable_house_ellipse([None, None, None])[1] == "abstain_missing_house_ellipse"
