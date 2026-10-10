from prototype.motion_approach_orientation import approach_direction


def test_approach_cue_requires_toward_house_and_temporal_order():
    assert approach_direction([350, 138], [335, 175], 195, 3909, 3912)[
        "proposed_delivery_side"] == "top"
    assert approach_direction([200, 300], [240, 260], 155, 2978, 2970)[
        "proposed_delivery_side"] is None
    assert approach_direction([240, 180], [250, 145], 155, 10, 15)[
        "proposed_delivery_side"] is None
    assert approach_direction([240, 280], [250, 240], 195, 10, 15)[
        "proposed_delivery_side"] == "bottom"
