from prototype.scripts.audit_overhead_board_coverage import contains, visible_bounds


def test_image_bounds_flip_with_scan_orientation():
    house = {"center_px": [320, 240], "outer_radius_px": 100}
    top = visible_bounds(house, "top")
    bottom = visible_bounds(house, "bottom")
    assert top["longitudinal"] == [-2.4, 1.19]
    assert bottom["longitudinal"] == [-1.19, 2.4]
    assert top["lateral"] == [-3.2, 3.19]
    assert bottom["lateral"] == [-3.19, 3.2]


def test_extended_envelope_needs_visible_guard_side():
    house = {"center_px": [320, 260], "outer_radius_px": 100}
    bounds = visible_bounds(house, "top")
    assert contains(bounds, {"lateral": [-1, 1], "longitudinal": [-1, 1]}) is False
    assert contains(bounds, {"lateral": [-1.25, 1.25], "longitudinal": [-3, 1]}) is False
    assert contains(bounds, {"lateral": [-1.25, 1.25], "longitudinal": [-2.5, 0.9]}) is True
