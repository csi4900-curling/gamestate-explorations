"""Calibration donors must remain in the same routed camera context."""

from registered_house_calibration import alignment_supported, nearest_donor


def test_nearest_donor_cannot_cross_origin_or_run():
    candidates = {
        "target": {"origin": "left_routed_proposal", "source_run_id": "R01"},
        "same": {"origin": "left_routed_proposal", "source_run_id": "R01"},
        "other_run": {"origin": "left_routed_proposal", "source_run_id": "R02"},
        "right": {"origin": "right_entry_review", "right_entry_ids": ["I01:R1"]},
    }
    accepted = [
        {"candidate_id": "other_run", "sample_times_s": [30, 35, 40]},
        {"candidate_id": "right", "sample_times_s": [30, 35, 40]},
        {"candidate_id": "same", "sample_times_s": [40, 45, 50]},
    ]
    target = {"candidate_id": "target", "sample_times_s": [30, 35, 40]}
    assert nearest_donor(target, accepted, candidates)["candidate_id"] == "same"
    assert nearest_donor(target, accepted[:2], candidates) is None


def test_alignment_requires_zero_shift_and_paint_overlap():
    alignment = {
        "zero_translation_is_best": True,
        "best_translation_second_to_first_px": [0, 0],
        "best_mask_iou": 0.8,
    }
    assert alignment_supported(alignment)
    alignment["best_translation_second_to_first_px"] = [1, 0]
    assert not alignment_supported(alignment)
    alignment["best_translation_second_to_first_px"] = [0, 0]
    alignment["best_mask_iou"] = 0.6
    assert not alignment_supported(alignment)
