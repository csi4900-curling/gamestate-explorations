from prototype.scripts.audit_right_coarse_window_overlap import overlaps


def test_overlap_requires_colour_time_and_reviewed_stone_pixels():
    events = [{"id": "E1", "colour": "yellow", "delivery_interval_s": [10, 20]},
              {"id": "E2", "colour": "red", "delivery_interval_s": [30, 40]}]
    proposals = [{"raw_track_id": "stone", "colour_claim": "yellow",
                  "passage": {"time_s": 15}},
                 {"raw_track_id": "person", "colour_claim": "yellow",
                  "passage": {"time_s": 16}},
                 {"raw_track_id": "wrong_colour", "colour_claim": "red",
                  "passage": {"time_s": 17}},
                 {"raw_track_id": "too_late", "colour_claim": "red",
                  "passage": {"time_s": 41}}]
    classes = {"stone": "stone_pixels_identity_uncertain",
               "person": "person_or_wheelchair",
               "wrong_colour": "moving_stone",
               "too_late": "moving_stone"}
    rows = overlaps(events, proposals, classes)
    assert [row["reviewed_stone_pixel_proposal_ids"] for row in rows] == [
        ["stone"], []]
