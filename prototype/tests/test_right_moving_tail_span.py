from prototype.right_moving_tail_span import moving_tail_spans


def point(t, y):
    return {"time_s": t, "pixel": [100, y], "bbox": [95, y - 4, 10, 8],
            "cap_area_px2": 30}


def test_long_static_prefix_becomes_short_sustained_moving_tail():
    points = [point(t, 100) for t in range(12)] + [point(12, 120),
              point(13, 145), point(14, 172), point(15, 200)]
    original = {"raw_track_id": "A1", "colour_claim": "yellow",
                "direction": "positive_y", "passage": {"time_s": 13},
                "observed_prefix_interval_s": [0, 14],
                "observed_prefix_points": points[:15], "seed_start_index": 0}
    probe = {"raw_tracks": [{"track_id": "A1", "colour": "yellow",
                             "points": points}],
             "directional_review_proposals": [original]}
    result = moving_tail_spans(probe)
    assert len(result) == 1
    assert result[0]["tail_extraction_status"] == "short_sustained_motion_from_long_prefix"
    assert result[0]["observed_prefix_interval_s"][0] >= 12
    assert len(result[0]["observed_prefix_points"]) >= 3
    assert result[0]["raw_track_id"] == "A1"


def test_short_prefix_is_preserved():
    original = {"raw_track_id": "A1", "passage": {"time_s": 2},
                "observed_prefix_interval_s": [1, 4]}
    probe = {"raw_tracks": [{"track_id": "A1", "points": [point(1, 10)]}],
             "directional_review_proposals": [original]}
    assert moving_tail_spans(probe)[0]["tail_extraction_status"] == \
        "original_short_prefix_retained"
