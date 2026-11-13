from nonorigin_continuity_rescue_v2 import rescue_phase_supported_nonorigin_shots


def test_phase_veto_rejects_moving_caps_in_unsupported_shot():
    track = {"colour": "red", "point_count": 12, "span_px": 100, "interval_s": [45, 47]}
    shots = [
        {"shot_id": "A", "interval_s": [0, 10], "same_shot_candidates": []},
        {"shot_id": "B", "interval_s": [45, 60], "same_shot_candidates": [track]},
        {"shot_id": "C", "interval_s": [60, 80], "same_shot_candidates": [track]},
    ]
    origins = {
        "A": {"predicted": 1, "probability": 0.9, "phase_supported": True},
        "B": {"predicted": 0, "probability": 0.3, "phase_supported": False},
        "C": {"predicted": 0, "probability": 0.01, "phase_supported": False},
    }
    assert rescue_phase_supported_nonorigin_shots(shots, origins, (0, 90)) == []
    origins["B"]["phase_supported"] = True
    assert [
        row["shot_id"] for row in rescue_phase_supported_nonorigin_shots(shots, origins, (0, 90))
    ] == ["B"]
