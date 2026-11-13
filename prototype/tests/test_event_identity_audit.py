from prototype.event_identity_audit import audit_event_identity


def test_flags_opposite_colour_following_motion_and_links_counter_without_merging():
    events = [
        {
            "candidate_id": "T1",
            "shot_id": "S1",
            "counter_id": None,
            "observation_anchor_s": 10,
            "release_window_s": [10, 20],
            "colour": "red",
            "broadcast_counter": None,
        },
        {
            "candidate_id": "T2",
            "shot_id": "S2",
            "counter_id": "B1",
            "observation_anchor_s": 30,
            "release_window_s": [30, 40],
            "colour": "yellow",
            "broadcast_counter": {"update_s": 35},
        },
    ]
    motion = [
        {
            "shot_id": "S1",
            "scanned": True,
            "same_shot_candidates": [],
            "following_shot_candidates": [
                {"colour": "yellow", "point_count": 30, "interval_s": [21, 30]}
            ],
        },
        {
            "shot_id": "S2",
            "scanned": False,
            "same_shot_candidates": [],
            "following_shot_candidates": [],
        },
    ]
    rows = audit_event_identity(events, motion)
    assert rows[0]["visual_only_colour_collision_risk"]
    assert rows[0]["earliest_following_colour_hypothesis"] == "yellow"
    assert rows[0]["possible_delayed_counter_links"] == [
        {
            "candidate_id": "T2",
            "counter_id": "B1",
            "colour": "yellow",
            "counter_update_lag_after_visual_window_s": 15,
        }
    ]
    assert rows[1]["visual_only_colour_collision_risk"] is False


def test_does_not_use_unscanned_or_distant_counter_as_negative_evidence():
    events = [
        {
            "candidate_id": "T1",
            "shot_id": "S1",
            "counter_id": None,
            "observation_anchor_s": 10,
            "release_window_s": [10, 20],
            "colour": "red",
            "broadcast_counter": None,
        },
        {
            "candidate_id": "T2",
            "shot_id": "S2",
            "counter_id": "B1",
            "observation_anchor_s": 100,
            "release_window_s": [100, 110],
            "colour": "yellow",
            "broadcast_counter": {"update_s": 110},
        },
    ]
    motion = [
        {
            "shot_id": "S1",
            "scanned": False,
            "same_shot_candidates": [],
            "following_shot_candidates": [
                {"colour": "yellow", "point_count": 30, "interval_s": [21, 30]}
            ],
        }
    ]
    rows = audit_event_identity(events, motion)
    assert rows[0]["ledger_colour_seen_in_same_shot_learned_motion"] is None
    assert rows[0]["visual_only_colour_collision_risk"] is False
    assert rows[0]["earliest_following_colour_hypothesis"] is None
    assert rows[0]["possible_delayed_counter_links"] == []
