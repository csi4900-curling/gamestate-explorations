from cross_resolution_path_overlap import (
    measure_all_co_sampled_pairs,
    measure_temporal_pair_overlap,
)


def test_exact_time_scaled_path_agreement_is_measured_without_identity_claim():
    left = [
        {
            "candidate_id": "S1",
            "selection": {
                "path": [
                    {"source_time_s": 1, "pixel_center": [900, 600]},
                    {"source_time_s": 2, "pixel_center": [906, 570]},
                ]
            },
        }
    ]
    right = [
        {
            "raw_track_id": "A001",
            "observed_prefix_points": [
                {"time_s": 1, "pixel": [300, 200]},
                {"time_s": 2, "pixel": [302, 190]},
            ],
        },
        {
            "raw_track_id": "A002",
            "observed_prefix_points": [
                {"time_s": 1, "pixel": [330, 200]},
                {"time_s": 2, "pixel": [332, 190]},
            ],
        },
    ]
    links = [
        {
            "left_candidate_id": "S1",
            "matching_right_proposals": [
                {"right_proposal_id": "R01:A001", "view_order_lag_s": 1.2}
            ],
        }
    ]
    scored = measure_temporal_pair_overlap(left, right, links)
    assert len(scored) == 1
    assert scored[0]["sampled_time_overlap_count"] == 2
    assert scored[0]["median_center_distance_px_360"] == 0
    assert not scored[0]["physical_stone_identity_verified"]
    all_pairs = measure_all_co_sampled_pairs(left, right, links)
    assert len(all_pairs) == 2
    assert [
        (
            r["right_proposal_id"],
            r["temporal_colour_direction_link"],
            r["median_center_distance_px_360"],
        )
        for r in all_pairs
    ] == [("R01:A001", True, 0), ("R01:A002", False, 30)]


def test_no_exact_time_overlap_remains_unmeasured():
    left = [
        {
            "candidate_id": "S1",
            "selection": {"path": [{"source_time_s": 1.5, "pixel_center": [900, 600]}]},
        }
    ]
    right = [
        {"raw_track_id": "A001", "observed_prefix_points": [{"time_s": 1, "pixel": [300, 200]}]}
    ]
    links = [
        {
            "left_candidate_id": "S1",
            "matching_right_proposals": [
                {"right_proposal_id": "R01:A001", "view_order_lag_s": 1.2}
            ],
        }
    ]
    row = measure_temporal_pair_overlap(left, right, links)[0]
    assert row["sampled_time_overlap_count"] == 0
    assert row["median_center_distance_px_360"] is None
    assert measure_all_co_sampled_pairs(left, right, links) == []
