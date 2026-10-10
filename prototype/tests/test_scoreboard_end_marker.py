import numpy as np
import pytest

from prototype.scoreboard_end_marker import (ARROW, fit_header_grid,
                                             panel_shift_evidence, read_active_end_marker)


def test_reads_marker_and_abstains_on_blank_or_occluded_frame():
    frame = np.full((360, 640, 3), 215, dtype=np.uint8)
    x = 399 + round(4 * 10.3)
    patch = frame[68:78, x:x + 9]
    patch[ARROW.astype(bool)] = 25
    assert read_active_end_marker(frame)["end"] == 5
    assert read_active_end_marker(np.full_like(frame, 215)) is None
    assert read_active_end_marker(np.full_like(frame, 30)) is None


def test_rejects_non_frame_input():
    with pytest.raises(ValueError, match="BGR"):
        read_active_end_marker(np.zeros((360, 640), dtype=np.uint8))


def test_fits_shifted_and_narrower_scoreboard_grid():
    frame = np.full((360, 640, 3), 180, dtype=np.uint8)
    for index in range(10):
        x = round(430 + index * 9.4)
        frame[39:53, x] = 30
    geometry = fit_header_grid([frame] * 5, 28)
    assert geometry is not None
    assert abs(geometry["header_base_x_px"] - 430) <= 2
    assert abs(geometry["slot_pitch_px"] - 9.4) <= 0.2


def test_panel_shift_requires_both_team_colours():
    frame = np.full((360, 640, 3), 180, dtype=np.uint8)
    frame[53:65, 392:422] = (0, 0, 220)
    assert panel_shift_evidence(frame) is None
    frame[66:79, 392:422] = (0, 210, 255)
    assert abs(panel_shift_evidence(frame)["shift_px"] - 28) <= 3
