"""Camera support controls whether a right path can corroborate a left event."""

import pytest

from camera_aware_right_fusion import fuse


def entry(id, t, colour="red"):
    return {"raw_track_id": id, "colour_claim": colour, "entry_crossing": {"time_s": t}}


def event(id, t, colour="red"):
    return {"id": id, "colour": colour, "crossing_time_s": t}


def test_supported_left_corrob_and_static_left_preserves_right_only_review():
    right = {
        "source_sha256": "same",
        "entry_review_proposals": [entry("R1", 110), entry("R2", 210)],
    }
    left = {"source_sha256": "same", "events": [event("S1", 100), event("S2", 200)]}
    coverage = {
        "source_sha256": "same",
        "revised_supported_runs": [{"interval_s": [0, 150]}],
        "newly_unsupported_intervals": [{"interval_s": [150, 250]}],
    }
    rows = fuse(right, left, coverage)
    assert rows[0]["fusion_status"] == "cross_view_time_colour_corrob"
    assert rows[0]["conditional_left_candidate_id"] == "S1"
    assert rows[1]["fusion_status"] == "right_only_left_static_review"
    assert rows[1]["conditional_left_candidate_id"] is None
    assert all(not row["simulation_ready"] for row in rows)


def test_two_right_paths_cannot_both_claim_one_left_event():
    right = {
        "source_sha256": "same",
        "entry_review_proposals": [entry("R1", 110), entry("R2", 112)],
    }
    left = {"source_sha256": "same", "events": [event("S1", 100)]}
    coverage = {
        "source_sha256": "same",
        "route": {"runs": [{"layout": "split_2024", "interval_s": [0, 200]}]},
    }
    rows = fuse(right, left, coverage)
    assert all(
        row["fusion_status"] == "ambiguous_multiple_right_entries_review"
        and row["conditional_left_candidate_id"] is None
        for row in rows
    )


def test_left_event_inside_freeze_cannot_corrob_later_supported_right_entry():
    right = {"source_sha256": "same", "entry_review_proposals": [entry("R1", 155)]}
    left = {"source_sha256": "same", "events": [event("S1", 145)]}
    coverage = {
        "source_sha256": "same",
        "revised_supported_runs": [{"interval_s": [0, 140]}, {"interval_s": [150, 250]}],
        "newly_unsupported_intervals": [{"interval_s": [140, 150]}],
    }
    row = fuse(right, left, coverage)[0]
    assert row["fusion_status"] == "right_only_prior_left_coverage_gap_review"
    assert row["conditional_left_candidate_id"] is None


def test_routed_gap_keeps_right_only_until_development_bridge_covers_both_times():
    right = {"source_sha256": "same", "entry_review_proposals": [entry("R1", 210)]}
    left = {"source_sha256": "same", "observed_events": [event("S1", 200)]}
    original = {
        "source_sha256": "same",
        "supported_runs": [
            {"layout": "split_2024", "interval_s": [0, 190]},
            {"layout": "split_2024", "interval_s": [220, 300]},
        ],
    }
    bridged = {
        "source_sha256": "same",
        "supported_runs": [{"layout": "split_2024", "interval_s": [0, 300]}],
    }
    assert fuse(right, left, original)[0]["fusion_status"] == "right_only_layout_unknown_review"
    row = fuse(right, left, bridged)[0]
    assert row["fusion_status"] == "cross_view_time_colour_corrob"
    assert row["conditional_left_candidate_id"] == "S1"


def test_fingerprint_mismatch_is_rejected():
    with pytest.raises(ValueError, match="fingerprints"):
        fuse(
            {"source_sha256": "a", "entry_review_proposals": []},
            {"source_sha256": "b", "events": []},
            {"source_sha256": "a", "route": {"runs": []}},
        )


def test_earlier_same_colour_right_motion_cannot_corrob_later_left_passage():
    # A synthetic proposal at the time of the earlier Czech right-view yellow
    # motion must not be joined to the later S76-like left passage.
    right = {"source_sha256": "same", "entry_review_proposals": [entry("R_before", 3109, "yellow")]}
    left = {"source_sha256": "same", "events": [event("S76", 3114.35, "yellow")]}
    coverage = {
        "source_sha256": "same",
        "route": {"runs": [{"layout": "split_2024", "interval_s": [3000, 3200]}]},
    }
    row = fuse(right, left, coverage)[0]
    assert row["fusion_status"] == "unmatched_supported_left_review"
    assert row["conditional_left_candidate_id"] is None


def test_supported_right_entry_after_left_coverage_gap_is_right_only_review():
    right = {"source_sha256": "same", "entry_review_proposals": [entry("R181", 6216.83, "yellow")]}
    left = {"source_sha256": "same", "events": []}
    coverage = {
        "source_sha256": "same",
        "revised_supported_runs": [{"interval_s": [6120, 6130]}, {"interval_s": [6210, 7020]}],
        "newly_unsupported_intervals": [],
    }
    row = fuse(right, left, coverage)[0]
    assert row["left_coverage_status"] == "left_supported"
    assert row["fusion_status"] == "right_only_prior_left_coverage_gap_review"
    assert row["conditional_left_candidate_id"] is None


def test_supported_entire_lookback_keeps_unmatched_classification():
    right = {"source_sha256": "same", "entry_review_proposals": [entry("R091", 2781.16, "red")]}
    left = {"source_sha256": "same", "events": []}
    coverage = {
        "source_sha256": "same",
        "route": {"runs": [{"layout": "split_2024", "interval_s": [2700, 2900]}]},
    }
    row = fuse(right, left, coverage)[0]
    assert row["fusion_status"] == "unmatched_supported_left_review"


def test_raw_track_ids_restart_in_separate_blind_intervals():
    right = {
        "source_sha256": "same",
        "intervals": [
            {"entry_review_proposals": [entry("R001", 110)]},
            {"entry_review_proposals": [entry("R001", 310)]},
        ],
    }
    left = {"source_sha256": "same", "observed_events": []}
    coverage = {
        "source_sha256": "same",
        "revised_supported_runs": [],
        "newly_unsupported_intervals": [{"interval_s": [100, 150]}, {"interval_s": [300, 350]}],
    }
    rows = fuse(right, left, coverage)
    assert [row["right_entry_id"] for row in rows] == ["I01:R001", "I02:R001"]
    assert all(row["fusion_status"] == "right_only_left_static_review" for row in rows)
