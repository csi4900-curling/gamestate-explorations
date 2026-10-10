from prototype.motion_episode_near_duplicates import find_near_duplicate_pairs


def episode(name, candidate, *, start=10, end=18, colour="red", first=(100, 200),
            last=(130, 180), span=36.0):
    return {"episode_id": name, "candidate_ids": [candidate], "colour": colour,
            "motion_interval_s": [start, end], "first_pixel": list(first),
            "last_pixel": list(last), "span_px": span}


def test_truncated_near_identical_track_is_flagged():
    pairs = find_near_duplicate_pairs([
        episode("M1", "S1", end=16),
        episode("M2", "S2", start=11, end=20, last=(131, 180)),
    ])
    assert [row["episode_ids"] for row in pairs] == [["M1", "M2"]]
    assert pairs[0]["same_physical_stone_verified"] is False


def test_time_only_or_colour_only_match_is_not_enough():
    pairs = find_near_duplicate_pairs([
        episode("M1", "S1"),
        episode("M2", "S2", first=(120, 200)),
        episode("M3", "S3", colour="yellow"),
        episode("M4", "S1", end=19),
    ])
    assert pairs == []


def test_nonoverlapping_track_is_not_flagged():
    assert find_near_duplicate_pairs([
        episode("M1", "S1", start=10, end=11),
        episode("M2", "S2", start=11, end=20),
    ]) == []
