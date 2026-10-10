import cv2
import numpy as np

from right_track_underpoint_context import three_sample_underpoint, underpoint_nonice_fraction


def test_underpoint_band_senses_support_below_without_coloured_cap():
    frame = np.full((360, 640, 3), 235, dtype=np.uint8)
    cv2.rectangle(frame, (300, 160), (339, 198), (25, 25, 160), -1)
    assert underpoint_nonice_fraction(frame, (320, 138)) > 0.9
    assert underpoint_nonice_fraction(frame, (250, 138)) == 0.0


def test_bottom_crop_abstains_and_three_samples_report_availability():
    frame = np.full((360, 640, 3), 235, dtype=np.uint8)
    assert underpoint_nonice_fraction(frame, (320, 355)) is None
    result = three_sample_underpoint(
        [frame] * 3, [{"pixel": [320, 100]}, {"pixel": [320, 355]}, {"pixel": [320, 110]}]
    )
    assert result["available_sample_count"] == 2
    assert result["median_underpoint_nonice_fraction"] == 0.0
