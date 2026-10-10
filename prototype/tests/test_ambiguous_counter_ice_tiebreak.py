from scripts.audit_2022_ambiguous_counter_ice_tiebreak import (
    select_unique_ice_supported,
)


def options():
    return [{"shot_id": "closeup", "origin_probability": 0.98,
             "max_center_lower_ice_fraction": 0.06},
            {"shot_id": "delivery", "origin_probability": 0.94,
             "max_center_lower_ice_fraction": 0.48},
            {"shot_id": "low_origin", "origin_probability": 0.04,
             "max_center_lower_ice_fraction": 0.8}]


def test_unique_ice_supported_choice_and_ambiguity_abstention():
    rows = options()
    assert select_unique_ice_supported(rows) == "delivery"
    rows[0]["max_center_lower_ice_fraction"] = 0.4
    assert select_unique_ice_supported(rows) is None
    rows[1]["max_center_lower_ice_fraction"] = 0.1
    assert select_unique_ice_supported(rows) == "closeup"
    rows[0]["max_center_lower_ice_fraction"] = 0.1
    assert select_unique_ice_supported(rows) is None
