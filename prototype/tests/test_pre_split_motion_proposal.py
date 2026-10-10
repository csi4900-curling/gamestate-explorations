from prototype.pre_split_motion_proposal import (
    deduplicate_identical_prefixes,
    propose_pre_split_motion,
)


def example(candidate_id="S01"):
    prefix = [
        {"source_time_s": 10.0, "pixel_center": [100, 100], "ground_position_m": [0.0, -3.0]},
        {"source_time_s": 10.5, "pixel_center": [105, 135], "ground_position_m": [0.0, -1.8]},
    ]
    motion = {
        "candidate_id": candidate_id,
        "colour": "red",
        "receiving_view": "left",
        "crossing_time_s": 5.0,
        "selection": {
            "status": "ambiguous_far_entry_motion_paths",
            "shared_prefix": prefix,
            "first_ambiguity_time_s": 11.0,
        },
    }
    patch = {
        "candidate_id": candidate_id,
        "samples": [
            {"source_time_s": t, "status": "scored", "patch_accepted": True} for t in (10.0, 10.5)
        ],
    }
    decision = {
        "candidate_id": candidate_id,
        "accepted": False,
        "status": "abstain_no_supported_motion_path",
    }
    return motion, patch, decision


def test_keeps_pre_split_observation_without_post_split_identity():
    proposal = propose_pre_split_motion(*example())
    assert proposal["prefix_sample_count"] == 2
    assert proposal["first_ambiguity_time_s"] == 11.0
    assert proposal["physical_throw_identity_verified"] is False
    assert proposal["post_split_stone_identity_verified"] is False


def test_rejects_weak_appearance_or_existing_decision():
    motion, patch, decision = example()
    patch["samples"][1]["patch_accepted"] = False
    assert propose_pre_split_motion(motion, patch, decision) is None
    patch["samples"][1]["patch_accepted"] = True
    decision["status"] = "duplicate_shared_timed_motion_path"
    assert propose_pre_split_motion(motion, patch, decision) is None
    decision["status"] = "abstain_no_supported_motion_path"
    decision["accepted"] = True
    assert propose_pre_split_motion(motion, patch, decision) is None


def test_collapses_only_identical_prefixes():
    a = propose_pre_split_motion(*example("S131"))
    b = propose_pre_split_motion(*example("S132"))
    b["crossing_time_s"] = 7.0
    c = propose_pre_split_motion(*example("S133"))
    c["prefix_samples"][1]["pixel_center"] = [106, 135]
    groups = deduplicate_identical_prefixes([c, b, a])
    assert [row["candidate_id"] for row in groups] == ["S131", "S133"]
    assert groups[0]["duplicate_candidate_ids"] == ["S132"]
