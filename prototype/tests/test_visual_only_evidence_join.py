import pytest

from prototype.visual_only_evidence_join import join_evidence


def patch(candidate, status):
    return {
        "candidate_id": candidate,
        "release_window_s": [1, 2],
        "candidate_colour": "red",
        "patch_evidence_status": status,
    }


def release(candidate, status):
    return {
        "candidate_id": candidate,
        "release_window_s": [1, 2],
        "candidate_colour": "red",
        "status": status,
    }


def test_neither_cue_is_retained():
    out = join_evidence(
        [patch("T1", "cap_tracks_without_stone_like_patch_support")],
        [release("T1", "no_colour_compatible_passage")],
    )
    assert out["rows"][0]["evidence_pattern"] == "neither_cue"
    assert out["rows"][0]["retained_for_event_review"]
    assert not out["rows"][0]["physical_throw_verified"]


def test_mismatched_ids_rejected():
    with pytest.raises(ValueError, match="IDs"):
        join_evidence(
            [patch("T1", "stone_like_patch_track_present")],
            [release("T2", "unique_colour_compatible_passage")],
        )
