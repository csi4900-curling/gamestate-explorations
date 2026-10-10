from prototype.event_evidence_tiers import event_evidence_tier


def test_counter_support_keeps_provisional_status():
    result = event_evidence_tier("B12", {}, {})
    assert result["tier"] == "counter_backed_provisional"
    assert result["physical_throw_verified"] is False


def test_counterless_two_view_colour_agreement_is_distinct():
    release = {"status": "unique_passage", "time_s": 42.2, "colour": "yellow"}
    receiver = {"status": "source_colour_concordant_identity_unverified", "colour": "yellow"}
    assert event_evidence_tier(None, release, receiver)["tier"] == "two_view_release_without_counter"
    assert event_evidence_tier(None, release, {**receiver, "colour": "red"})["tier"] == "visual_window_only_unconfirmed"
    assert event_evidence_tier(None, {**release, "time_s": None}, receiver)["tier"] == "visual_window_only_unconfirmed"
