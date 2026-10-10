"""Counter coverage distinguishes unreadable seconds from observed play."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_beijing_counter_full import visibility_runs


def test_visibility_runs_preserve_each_unreadable_span():
    samples = [
        {"time_s": 10, "counts": None},
        {"time_s": 11, "counts": [8, 8]},
        {"time_s": 12, "counts": [8, 8]},
        {"time_s": 13, "counts": None},
    ]
    assert visibility_runs(samples) == [
        {"visible": False, "interval_s": [10, 11], "samples": 1},
        {"visible": True, "interval_s": [11, 13], "samples": 2},
        {"visible": False, "interval_s": [13, 14], "samples": 1},
    ]
