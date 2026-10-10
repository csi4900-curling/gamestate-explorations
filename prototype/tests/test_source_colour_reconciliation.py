from prototype.source_colour_reconciliation import reconcile_event_colour


RELEASE = {"status": "unique_passage", "time_s": 12.4, "colour": "yellow"}
RECEIVING = {"status": "source_colour_concordant_identity_unverified", "colour": "yellow"}


def test_two_agreeing_views_correct_and_preserve_a_conflicting_label():
    result = reconcile_event_colour("red", RELEASE, RECEIVING)
    assert result["colour"] == "yellow"
    assert result["original_colour"] == "red"
    assert result["status"] == "source_two_view_colour_corrected"
    assert result["physical_stone_identity_verified"] is False


def test_two_agreeing_views_fill_missing_colour():
    result = reconcile_event_colour(None, RELEASE, RECEIVING)
    assert result["colour"] == "yellow"
    assert result["status"] == "source_two_view_colour_filled"


def test_single_or_disagreeing_cues_do_not_override():
    assert (
        reconcile_event_colour("red", RELEASE, {"status": "not_scanned", "colour": None})["colour"]
        == "red"
    )
    assert reconcile_event_colour("red", RELEASE, {**RECEIVING, "colour": "red"})["colour"] == "red"
    assert reconcile_event_colour("red", {**RELEASE, "time_s": None}, RECEIVING)["colour"] == "red"
