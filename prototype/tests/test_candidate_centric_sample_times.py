import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_candidate_centric_receiving_motion import sample_times


def test_samples_only_after_candidate_and_stays_in_interval():
    assert sample_times(10.2, 30, 4) == [11, 12, 13, 14]
    assert sample_times(27.3, 30, 12) == [28, 29, 30]
    assert sample_times(10.2, 12, 4, 0.5) == [10.5, 11.0, 11.5, 12.0]
