from right_multi_episode_span import multi_episode_spans


def point(t, y):
    return {
        "time_s": float(t),
        "pixel": [400.0, float(y)],
        "bbox": [395, int(y), 10, 6],
        "cap_area_px2": 20.0,
    }


def track(points):
    return {"track_id": "A001", "colour": "red", "points": points, "span_px": 200.0}


def test_two_motion_episodes_separated_by_quiet_are_both_proposed():
    points = [point(0, 300), point(1, 270), point(2, 240), point(3, 210)]
    points += [point(t, 210) for t in range(4, 12)]
    points += [point(12, 230), point(13, 255), point(14, 280)]
    found = multi_episode_spans([track(points)])
    assert len(found) == 2
    assert [row["episode_index_within_raw_track"] for row in found] == [1, 2]
    assert [row["direction"] for row in found] == ["negative_y", "positive_y"]
    assert found[1]["preceding_quiet_end_time_s"] is not None


def test_continuous_motion_does_not_produce_another_span():
    points = [point(t, 300 - 22 * t) for t in range(12)]
    found = multi_episode_spans([track(points)])
    assert len(found) == 1


def test_nonincreasing_track_time_is_rejected():
    try:
        multi_episode_spans([track([point(0, 300), point(0, 280)])])
    except ValueError as error:
        assert "times must increase" in str(error)
    else:
        raise AssertionError("Duplicate raw observation time was accepted")
