"""Conservative image-space approach-direction cue for one tracked stone."""


def approach_direction(first_pixel, last_pixel, house_center_y, track_last_s,
                       stable_first_s, *, min_side_px=10.0,
                       min_travel_px=15.0, min_approach_px=15.0,
                       settle_gap_tolerance_s=2.0):
    first_y = float(first_pixel[1])
    last_y = float(last_pixel[1])
    center = float(house_center_y)
    travel = last_y - first_y
    approach = abs(first_y - center) - abs(last_y - center)
    side = ("top" if first_y < center - min_side_px and travel > min_travel_px
            else "bottom" if first_y > center + min_side_px and travel < -min_travel_px
            else None)
    if (side is None or approach <= min_approach_px or
            track_last_s > stable_first_s + settle_gap_tolerance_s):
        side = None
    return {"proposed_delivery_side": side,
            "vertical_travel_px": round(travel, 2),
            "distance_to_later_house_center_reduction_px": round(approach, 2),
            "track_ends_before_stable_board": track_last_s <= stable_first_s + settle_gap_tolerance_s}
