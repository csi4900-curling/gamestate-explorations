import pytest

from prototype.end_display_context import annotate_display_context


def marker(time_s, end):
    return {"time_s": time_s, "marker": {"end": end}}


def event(identifier, time_s):
    return {"id": identifier, "crossing_time_s": time_s}


def test_only_local_agreement_supplies_display_end():
    rows = annotate_display_context(
        [event("same", 15), event("change", 45), event("far", 130)],
        [marker(10, 2), marker(20, 2), marker(40, 2), marker(50, 3)],
    )
    assert [row["display_context_status"] for row in rows] == [
        "bracketed_display_end",
        "bracketed_display_change",
        "display_context_unknown",
    ]
    assert [row["displayed_end"] for row in rows] == [2, None, None]
    assert all(row["physical_end"] is None for row in rows)


def test_isolated_wrong_marker_can_be_excluded_without_changing_raw_samples():
    samples = [marker(10, 3), marker(20, 1), marker(30, 3)]
    raw = annotate_display_context([event("A", 25)], samples)
    cleaned = annotate_display_context([event("A", 25)], samples, ignored_marker_times_s=[20])
    assert raw[0]["display_context_status"] == "bracketed_display_change"
    assert cleaned[0]["displayed_end"] == 3
    assert samples[1]["marker"]["end"] == 1


def test_rejects_nonincreasing_marker_times():
    with pytest.raises(ValueError, match="increasing"):
        annotate_display_context([], [marker(10, 1), marker(10, 2)])
