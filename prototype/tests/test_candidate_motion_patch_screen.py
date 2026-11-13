import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from candidate_motion_patch_screen import screen_candidate


def motion(status):
    return {"candidate_id": "D1", "selection": {"status": status, "sample_count": 5}}


def patch(*values):
    return {
        "candidate_id": "D1",
        "samples": [{"status": "scored", "patch_accepted": value} for value in values],
    }


def test_requires_both_unique_motion_and_one_positive_patch():
    good = screen_candidate(
        motion("provisional_unique_far_entry_motion_path"), patch(False, True, False)
    )
    assert good["accepted"]
    assert good["physical_identity_verified"] is False
    assert not screen_candidate(
        motion("provisional_unique_far_entry_motion_path"), patch(False, False)
    )["accepted"]
    assert not screen_candidate(motion("no_supported_far_entry_motion_path"), patch(True))[
        "accepted"
    ]


def test_incomplete_patch_abstains_and_id_mismatch_fails():
    row = {"candidate_id": "D1", "samples": [{"status": "no_unique_matching_cap"}]}
    assert (
        screen_candidate(motion("provisional_unique_far_entry_motion_path"), row)["status"]
        == "abstain_incomplete_patch_check"
    )
    with pytest.raises(ValueError):
        screen_candidate(
            motion("provisional_unique_far_entry_motion_path"),
            {"candidate_id": "D2", "samples": []},
        )
