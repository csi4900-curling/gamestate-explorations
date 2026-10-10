from prototype.official_shot_gap_audit import build_gap_runs


def test_groups_unanchored_shots_and_keeps_counter_conflict():
    game = {
        "team_handle_colours": {"A": "red", "B": "yellow"},
        "ends": [
            {
                "end": 1,
                "shot_count": 5,
                "shots": [
                    {"official_shot_id": f"S{i}", "team": "A" if i % 2 else "B"}
                    for i in range(1, 6)
                ],
            }
        ],
    }
    rows = [
        {
            "official_end": 1,
            "inferred_shot_number": number,
            "status": status,
            "counter_id": f"B{number}",
            "counter_time_s": time,
        }
        for number, status, time in [
            (1, "unique_colour_concordant", 10),
            (2, "duplicate_counter_slot", 20),
            (4, "unique_colour_concordant", 40),
        ]
    ]
    candidates = [
        {
            "candidate_id": "T1",
            "release_window_s": [25, 30],
            "colour": "yellow",
            "counter_id": None,
        },
        {"candidate_id": "T2", "release_window_s": [41, 45], "colour": "red", "counter_id": None},
    ]
    runs = build_gap_runs(game, rows, candidates)
    assert [(r["first_shot_number"], r["last_shot_number"]) for r in runs] == [(2, 3), (5, 5)]
    assert runs[0]["review_search_span_s"] == [10, 40]
    assert runs[0]["conflicting_counter_ids"] == ["B2"]
    assert [c["candidate_id"] for c in runs[0]["candidate_windows_intersecting_span"]] == ["T1"]
    assert runs[0]["visual_candidate_triage"] == "multiple_or_multishot_visual_candidates"
    assert runs[1]["bounded_within_end"] is False
    assert runs[1]["candidate_windows_intersecting_span"] == []
