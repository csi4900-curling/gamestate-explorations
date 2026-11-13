"""Guard source-only cap associations from becoming game-state claims."""

from right_board_sequence import build_right_board_sequence


def cap(local_id, x):
    return {"local_observation_id": local_id, "colour": "red", "pixel_center": [x, 200]}


def fixture():
    union = {
        "source_sha256": "source",
        "candidates": [
            {
                "candidate_id": "RIGHT-I01:R1",
                "origin": "right_entry_review",
                "right_entry_ids": ["I01:R1"],
                "source_time_s": 10,
            },
            {
                "candidate_id": "RIGHT-I01:R2",
                "origin": "right_entry_review",
                "right_entry_ids": ["I01:R2"],
                "source_time_s": 30,
            },
        ],
    }
    boards = {
        "source_sha256": "source",
        "rows": [
            {
                "right_entry_id": "I01:R1",
                "entry_time_s": 10,
                "observation_status": "partial_stable_colour_cap_proposals",
                "stable_cap_proposals": [cap("C1", 400)],
            },
            {
                "right_entry_id": "I01:R2",
                "entry_time_s": 30,
                "observation_status": "partial_stable_colour_cap_proposals",
                "stable_cap_proposals": [cap("C2", 401), cap("C3", 450)],
            },
        ],
    }
    alignment = [
        {
            "before_right_entry_id": "I01:R1",
            "after_right_entry_id": "I01:R2",
            "status": "painted_ring_alignment_probe",
            "zero_translation_is_best": True,
            "best_translation_second_to_first_px": [0, 0],
            "best_mask_iou": 0.9,
        }
    ]
    return union, boards, alignment


def test_conditional_image_change_preserves_physical_unknown():
    result = build_right_board_sequence(*fixture())
    row = result["transitions"][0]
    assert row["status"] == "conditional_image_pixel_cap_association"
    assert row["matched_local_caps"][0]["before_local_cap_id"] == "C1"
    assert row["after_only_local_cap_ids"] == ["C3"]
    assert not row["physical_board_transition_verified"]
    assert not row["simulation_ready"]


def test_intervening_candidate_blocks_comparison():
    union, boards, alignment = fixture()
    union["candidates"].append(
        {"candidate_id": "LEFT", "origin": "left_routed_proposal", "source_time_s": 20}
    )
    row = build_right_board_sequence(union, boards, alignment)["transitions"][0]
    assert row["status"] == "abstain_intervening_candidate"
    assert row["intervening_candidate_ids"] == ["LEFT"]


def test_camera_alignment_and_interval_change_block_comparison():
    union, boards, alignment = fixture()
    alignment[0]["best_mask_iou"] = 0.5
    assert (
        build_right_board_sequence(union, boards, alignment)["transitions"][0]["status"]
        == "abstain_house_image_alignment"
    )
    boards["rows"][1]["right_entry_id"] = "I02:R2"
    union["candidates"][1]["right_entry_ids"] = ["I02:R2"]
    alignment[0]["after_right_entry_id"] = "I02:R2"
    assert (
        build_right_board_sequence(union, boards, alignment)["transitions"][0]["status"]
        == "abstain_route_interval_change"
    )


def test_two_old_caps_leave_shared_new_cap_ambiguous():
    union, boards, alignment = fixture()
    boards["rows"][0]["stable_cap_proposals"].append(cap("C4", 402))
    row = build_right_board_sequence(union, boards, alignment)["transitions"][0]
    assert row["status"] == "conditional_image_pixel_cap_association"
    assert row["matched_local_caps"] == []
    assert row["ambiguous_before_local_cap_ids"] == ["C1", "C4"]
    assert row["ambiguous_after_local_cap_ids"] == ["C2"]
