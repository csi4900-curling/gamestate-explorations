"""Check that a lost prefix is retained only with independent appearance support."""

from candidate_prefix_fallback import propose_original_prefix


def evidence(positive=(True, True, False)):
    prefix = [{"source_time_s": i, "ground_position_m": [i, 0]} for i in range(5)]
    base = {
        "candidate_id": "S02",
        "receiving_view": "left",
        "colour": "red",
        "selection": {
            "status": "ambiguous_far_entry_motion_paths",
            "shared_prefix": prefix,
            "best_path_sample_count": 7,
            "first_ambiguity_time_s": 5,
        },
    }
    retry = {"candidate_id": "S02", "rescue_status": "rescue_abstained"}
    patch = {
        "candidate_id": "S02",
        "samples": [
            {"source_time_s": i, "status": "scored", "patch_accepted": good}
            for i, good in enumerate(positive)
        ],
    }
    return base, retry, patch


def test_keeps_only_supported_original_prefix():
    result = propose_original_prefix(*evidence())
    assert result["prefix_sample_count"] == 5
    assert result["motion_after_ambiguity_verified"] is False
    assert result["physical_throw_identity_verified"] is False


def test_weak_appearance_does_not_promote_prefix():
    assert propose_original_prefix(*evidence((False, True, False))) is None


def test_short_path_does_not_promote_prefix():
    args = list(evidence())
    args[0]["selection"]["shared_prefix"] = args[0]["selection"]["shared_prefix"][:4]
    assert propose_original_prefix(*args) is None
