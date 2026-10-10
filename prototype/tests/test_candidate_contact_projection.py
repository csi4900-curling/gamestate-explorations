"""Repeated body-bottom evidence must be stable before plane projection."""

from candidate_contact_projection import stable_body_bottom


def contact(x, y):
    return {"pixel": [x, y], "supporting_body_rows": 5,
            "bottom_row_body_pixels": 12}


def test_three_stable_contacts_yield_only_a_proxy():
    result, status = stable_body_bottom([
        contact(490, 215), contact(491, 216), contact(490, 216)])
    assert status == "conditional_repeated_body_bottom_proxy"
    assert result["body_bottom_pixel_median"] == [490, 216]
    assert result["body_bottom_proxy_not_verified_ice_contact"]


def test_missing_or_moving_body_abstains():
    assert stable_body_bottom([contact(490, 215), None, contact(490, 216)])[1] == \
        "abstain_missing_body_bottom_in_three_frames"
    assert stable_body_bottom([
        contact(490, 215), contact(495, 215), contact(490, 215)])[1] == \
        "abstain_unstable_body_bottom"
