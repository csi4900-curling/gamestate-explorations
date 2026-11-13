from copy import deepcopy

import pytest

from event_board_evidence import link_event_boards


def fixtures():
    board = {
        "observation_id": "B1",
        "source_video_sha256": "a" * 64,
        "source_recording_code": "G",
        "counter_anchor_s": 42.0,
        "observation_interval_s": [48.0, 52.0],
        "stones": [{"colour": "red"}],
        "coordinate_frame": {"unit": "detected_outer_house_radius"},
        "state_status": "partial_video_observation",
        "completeness": "unknown_from_video",
        "simulation_ready": False,
    }
    event = {
        "candidate_id": "T1",
        "colour": "red",
        "colour_status": "resolved",
        "evidence_class": "origin_view_candidate",
        "release_window_s": [30, 40],
        "observation_anchor_s": 32,
        "counter_id": "C1",
        "broadcast_counter": {"update_s": 42.0},
    }
    ledger = {"source_sha256": "a" * 64, "events": [event]}
    return board, ledger


def test_exact_counter_join_preserves_uncertainty():
    board, ledger = fixtures()
    result = link_event_boards([board], [ledger])[0]
    assert result["link_status"] == "unique_shared_delayed_counter"
    assert result["event_candidates"][0]["candidate_id"] == "T1"
    assert result["delivered_stone_identity"] is None
    assert result["simulation_ready"] is False


def test_duplicate_or_missing_counter_is_not_silently_resolved():
    board, ledger = fixtures()
    second = deepcopy(ledger["events"][0])
    second["candidate_id"] = "T2"
    ledger["events"].append(second)
    assert link_event_boards([board], [ledger])[0]["link_status"] == (
        "ambiguous_shared_delayed_counter"
    )
    board["counter_anchor_s"] = 43.0
    assert link_event_boards([board], [ledger])[0]["link_status"] == ("no_shared_delayed_counter")


def test_rejects_missing_source_and_unsupported_readiness_claim():
    board, ledger = fixtures()
    with pytest.raises(ValueError, match="No event ledger"):
        link_event_boards([board], [])
    board["simulation_ready"] = True
    with pytest.raises(ValueError, match="unsupported simulation"):
        link_event_boards([board], [ledger])
