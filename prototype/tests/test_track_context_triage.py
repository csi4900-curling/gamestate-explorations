import pytest

from track_context_triage import classify_context


def test_three_way_context_cue_preserves_ambiguity():
    assert classify_context(-0.20) == "isolated_motion_cue"
    assert classify_context(0.20) == "comoving_context_review"
    assert classify_context(0) == "ambiguous_context"
    assert classify_context(None) == "abstain_insufficient_motion"


def test_rejects_overlapping_cue_bounds():
    with pytest.raises(ValueError):
        classify_context(0, isolated_at=0.2, comoving_at=0.2)
