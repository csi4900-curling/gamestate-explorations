"""Image-cap continuity abstains over missing snapshots and ambiguous links."""

from right_view_cap_sequence import adjacent_cap_sequence, compare_cap_sets


def cap(id, colour, x, y):
    return {"local_observation_id": id, "colour": colour,
            "pixel_center": [x, y]}


def row(id, t, status, caps):
    return {"right_raw_track_id": id, "entry_time_s": t,
            "observation_status": status, "stable_cap_proposals": caps}


def alignment(before, after, *, shift=(0, 0), iou=0.8):
    return {"before_right_track_id": before,
            "after_right_track_id": after,
            "status": "painted_ring_alignment_probe",
            "zero_translation_is_best": shift == (0, 0),
            "best_translation_second_to_first_px": list(shift),
            "best_mask_iou": iou}


def test_same_colour_unique_nearby_cap_association_is_not_identity():
    result = compare_cap_sets([cap("C01", "red", 400, 200)],
                              [cap("C02", "red", 403, 201),
                               cap("C03", "yellow", 400, 200)])
    assert len(result["matched_local_caps"]) == 1
    assert not result["matched_local_caps"][0]["physical_stone_identity_verified"]
    assert result["after_only_local_cap_ids"] == ["C03"]


def test_ambiguous_nearby_caps_are_not_matched():
    result = compare_cap_sets([cap("C01", "red", 400, 200),
                               cap("C02", "red", 403, 200)],
                              [cap("C03", "red", 401, 200)])
    assert result["matched_local_caps"] == []
    assert result["ambiguous_before_local_cap_ids"] == ["C01", "C02"]
    assert result["ambiguous_after_local_cap_ids"] == ["C03"]


def test_abstained_middle_entry_blocks_cross_gap_comparison():
    rows = [row("R1", 100, "partial_stable_colour_cap_proposals",
                [cap("C01", "red", 400, 200)]),
            row("R2", 150, "abstain_scene_or_player_motion", []),
            row("R3", 200, "partial_stable_colour_cap_proposals",
                [cap("C01", "red", 400, 200)])]
    transitions = adjacent_cap_sequence(rows, [
        alignment("R1", "R2"), alignment("R2", "R3")])
    assert len(transitions) == 2
    assert all(t["status"] == "abstain_missing_usable_cap_set" for t in transitions)
    assert all(not t["simulation_ready"] for t in transitions)


def test_shifted_house_abstains_even_when_caps_are_nearby():
    rows = [row("R1", 100, "partial_stable_colour_cap_proposals",
                [cap("C01", "red", 400, 200)]),
            row("R2", 150, "partial_stable_colour_cap_proposals",
                [cap("C02", "red", 400, 200)])]
    result = adjacent_cap_sequence(rows, [alignment("R1", "R2", shift=(2, 0))])
    assert result[0]["status"] == "abstain_house_image_alignment"
    assert "matched_local_caps" not in result[0]


def test_weak_house_overlap_abstains():
    rows = [row("R1", 100, "partial_stable_colour_cap_proposals", []),
            row("R2", 150, "partial_stable_colour_cap_proposals", [])]
    result = adjacent_cap_sequence(rows, [alignment("R1", "R2", iou=0.3)])
    assert result[0]["status"] == "abstain_house_image_alignment"


def test_aligned_house_allows_conditional_comparison_only():
    rows = [row("R1", 100, "partial_stable_colour_cap_proposals",
                [cap("C01", "red", 400, 200)]),
            row("R2", 150, "partial_stable_colour_cap_proposals",
                [cap("C02", "red", 400, 200)])]
    result = adjacent_cap_sequence(rows, [alignment("R1", "R2")])[0]
    assert result["status"] == "conditional_image_pixel_cap_association"
    assert result["sampled_house_alignment_supported"]
    assert not result["same_camera_pose_verified"]
    assert not result["simulation_ready"]
