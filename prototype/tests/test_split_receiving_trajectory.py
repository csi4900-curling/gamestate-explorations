import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from split_receiving_trajectory import incoming_crossing


def samples(values):
    return [
        {"time_s": i * 0.5, "top_view_m": [0, y] if y is not None else None}
        for i, y in enumerate(values)
    ]


def test_incoming_hog_crossing_needs_forward_motion_not_parked_stone():
    assert incoming_crossing(samples([8, 7, 6, 5])) == pytest.approx(0.7995)
    assert incoming_crossing(samples([5, 6, 7, 8])) is None
    assert incoming_crossing(samples([0.5, 0.5, 0.5, 0.5])) is None
    assert incoming_crossing(samples([6.42, 6.40, 6.39])) is None
    assert incoming_crossing(samples([8, None, None, None, 5])) is None
