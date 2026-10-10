from prototype.right_context_tier import context_tier


def test_context_tier_abstains_when_missing_and_flags_either_clutter_measure():
    assert context_tier(0.1, 0.1) == "clear_context_review"
    assert context_tier(0.26, 0.1) == "context_cluttered_review"
    assert context_tier(0.1, 0.26) == "context_cluttered_review"
    assert context_tier(0.1, None) == "context_unavailable_review"
