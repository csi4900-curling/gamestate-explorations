"""Post-entry board samples must not cross the next right entry."""

from scripts.scan_scotland_right_entry_boards import eligible_tail


def test_tail_abstains_when_next_entry_overlaps_sample_guard():
    assert eligible_tail(100.0, 129.0, 300.0) == "abstain_next_right_entry"
    assert eligible_tail(100.0, 130.0, 300.0) is None


def test_tail_abstains_at_source_end():
    assert eligible_tail(100.0, None, 125.0) == "abstain_source_end"
