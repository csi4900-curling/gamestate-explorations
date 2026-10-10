from right_global_area_tracks import global_area_tracks


def candidate(x, y, area=80):
    return {"pixel": [x, y], "bbox": [int(x - 5), int(y - 4), 10, 8], "cap_area_px2": area}


def test_competing_old_track_cannot_steal_better_moving_stone_match():
    observations = [
        (0, [candidate(385, 149, 40), candidate(424, 225, 110)]),
        (1, [candidate(385, 149, 40), candidate(422, 205, 83)]),
        (2, [candidate(420, 186, 80)]),
        (3, [candidate(417, 169, 85)]),
        (4, [candidate(409, 146, 7)]),
    ]
    tracks = global_area_tracks(observations)
    assert any([p["pixel"][1] for p in t["points"]][:4] == [225, 205, 186, 169] for t in tracks)


def test_area_term_still_prefers_moving_cap_over_nearer_small_blob():
    observations = [
        (0, [candidate(400, 208, 60)]),
        (1, [candidate(400, 190, 9), candidate(400, 231, 17)]),
        (2, [candidate(400, 262, 44)]),
        (3, [candidate(400, 296, 39)]),
    ]
    tracks = global_area_tracks(observations)
    assert any([p["pixel"][1] for p in t["points"]] == [208, 231, 262, 296] for t in tracks)
