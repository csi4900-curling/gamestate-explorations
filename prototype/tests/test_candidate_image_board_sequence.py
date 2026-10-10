"""Only adjacent, aligned image observations may yield cap associations."""

from candidate_image_board_sequence import compare_candidate_boards


def candidate(cid, time, x, *, origin="left_routed_proposal", run="R01"):
    return {"candidate_id": cid, "source_time_s": time, "origin": origin,
            "source_run_id": run, "right_entry_ids": ["I01:R1"],
            "post_candidate_image_observation": {
                "status": "partial_stable_colour_cap_proposals",
                "sample_times_s": [time + 15, time + 20, time + 25],
                "stable_cap_proposals": [{"local_observation_id": "C1",
                                          "colour": "red", "pixel_center": [x, 200]}]}}


def fixture():
    handoff = {"source_sha256": "source", "ordered_candidates": [
        candidate("A", 10, 400), candidate("B", 50, 401)]}
    alignment = [{"before_candidate_id": "A", "after_candidate_id": "B",
                  "status": "painted_ring_alignment_probe",
                  "zero_translation_is_best": True,
                  "best_translation_second_to_first_px": [0, 0],
                  "best_mask_iou": 0.9}]
    return handoff, alignment


def test_adjacent_image_caps_match_without_promoting_physical_state():
    row = compare_candidate_boards(*fixture())["transitions"][0]
    assert row["status"] == "conditional_image_pixel_cap_association"
    assert len(row["matched_local_caps"]) == 1
    assert not row["physical_board_transition_verified"]


def test_camera_and_timing_guards_abstain():
    handoff, alignment = fixture()
    alignment[0]["best_mask_iou"] = 0.5
    assert compare_candidate_boards(handoff, alignment)["transitions"][0][
        "status"] == "abstain_house_image_alignment"
    handoff, alignment = fixture()
    handoff["ordered_candidates"][1]["source_time_s"] = 30
    assert compare_candidate_boards(handoff, alignment)["transitions"][0][
        "status"] == "abstain_overlapping_or_late_board_samples"


def test_route_and_origin_change_abstain():
    handoff, alignment = fixture()
    handoff["ordered_candidates"][1]["source_run_id"] = "R02"
    assert compare_candidate_boards(handoff, alignment)["transitions"][0][
        "status"] == "abstain_route_run_change"
    handoff, alignment = fixture()
    handoff["ordered_candidates"][1]["origin"] = "right_entry_review"
    assert compare_candidate_boards(handoff, alignment)["transitions"][0][
        "status"] == "abstain_origin_change"
