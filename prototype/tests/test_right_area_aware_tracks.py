from right_area_aware_tracks import area_aware_tracks


def candidate(y, area):
    return {"pixel": [400, y], "bbox": [394, y - 4, 12, 8],
            "cap_area_px2": area}


def test_area_continuity_keeps_moving_cap_when_static_blob_is_nearer():
    observations = [
        (0, [candidate(208, 60)]),
        (1, [candidate(190, 9), candidate(231, 17)]),
        (2, [candidate(190, 9), candidate(262, 44)]),
        (3, [candidate(190, 9), candidate(296, 39)]),
    ]
    tracks = area_aware_tracks(observations)
    assert any([point["pixel"][1] for point in track["points"]] ==
               [208, 231, 262, 296] for track in tracks)


def test_short_recovered_moving_track_can_have_three_observations():
    observations = [(0, [candidate(231, 17)]),
                    (1, [candidate(262, 44)]),
                    (2, [candidate(296, 39)])]
    tracks = area_aware_tracks(observations)
    assert len(tracks) == 1
    assert tracks[0]["span_px"] >= 60
