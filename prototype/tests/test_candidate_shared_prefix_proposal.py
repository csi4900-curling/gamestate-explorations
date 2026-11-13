from prototype.candidate_shared_prefix_proposal import propose_shared_prefix


def evidence():
    prefix = [{"source_time_s": float(i), "ground_position_m": [0.0, float(i)]} for i in range(5)]
    motion = {
        "candidate_id": "S1",
        "colour": "red",
        "receiving_view": "right",
        "selection": {
            "status": "ambiguous_far_entry_motion_paths",
            "shared_prefix": prefix,
            "best_path_sample_count": 6,
            "first_ambiguity_time_s": 5.0,
        },
    }
    patch = {
        "candidate_id": "S1",
        "samples": [
            {"source_time_s": float(i), "status": "scored", "patch_accepted": i > 0}
            for i in range(3)
        ],
    }
    return motion, patch


def test_long_stone_like_prefix_is_review_proposal_only():
    motion, patch = evidence()
    result = propose_shared_prefix(motion, patch)
    assert result["prefix_sample_count"] == 5
    assert result["positive_patch_count"] == 2
    assert result["physical_throw_identity_verified"] is False
    assert result["simulation_ready"] is False


def test_outside_prefix_patches_cannot_rescue_ambiguous_motion():
    motion, patch = evidence()
    patch["samples"][1]["source_time_s"] = 7.0
    assert propose_shared_prefix(motion, patch) is None
