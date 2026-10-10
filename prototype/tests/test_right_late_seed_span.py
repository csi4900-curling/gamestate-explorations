from right_late_seed_span import late_seed_bidirectional_spans


def point(t, y, area=20, width=10, height=6):
    return {"time_s": t, "pixel": [400, y], "bbox": [395, int(y), width, height],
            "cap_area_px2": area}


def test_later_seed_recovers_motion_after_long_static_prefix():
    track = {"track_id": "B001", "colour": "yellow", "points": [
        point(t, 200) for t in range(30)] + [
            point(30, 225), point(31, 250), point(32, 275)]}
    found = late_seed_bidirectional_spans([track])
    assert len(found) == 1
    assert found[0]["seed_start_index"] > 0
    assert found[0]["direction"] == "positive_y"


def test_small_initial_cap_can_grow_into_valid_seed():
    track = {"track_id": "B002", "colour": "red", "points": [
        point(0, 300, area=8), point(1, 270), point(2, 240), point(3, 210)]}
    found = late_seed_bidirectional_spans([track])
    assert len(found) == 1
    assert found[0]["seed_start_index"] == 1
    assert found[0]["direction"] == "negative_y"
