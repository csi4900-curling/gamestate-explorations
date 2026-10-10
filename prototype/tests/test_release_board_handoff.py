import pytest

from release_board_handoff import join_release_boards


def inputs(cue_s):
    board = {"board_observation_id": "board-1", "source_video_sha256": "hash",
             "source_recording_code": "game", "event_candidates": [{"counter_id": "B01"}],
             "board_observation_interval_s": [20, 25], "board_stone_count": 2}
    union = {"source_sha256": "hash", "official_game_code": "game",
             "events": [{"event_id": "VISUAL-S1", "counter_id": "B01",
                         "candidate_class": "visual_origin_existing"}]}
    release = {"source_sha256": "hash",
               "rows": [{"event_id": "VISUAL-S1", "unique_release_cue_s": cue_s,
                         "unique_passage_colour": "yellow" if cue_s else None}]}
    return [board], [union], [release]


def test_release_cue_precedes_partial_board_without_identity_claim():
    row = join_release_boards(*inputs(12))[0]
    assert row["release_cue_status"] == "cue_precedes_board"
    assert row["cue_to_board_start_s"] == 8
    assert row["simulation_ready"] is False


def test_missing_cue_remains_explicit_and_source_mismatch_rejected():
    row = join_release_boards(*inputs(None))[0]
    assert row["release_cue_status"] == "no_unique_passage"
    boards, unions, releases = inputs(12)
    releases[0]["source_sha256"] = "other"
    with pytest.raises(ValueError, match="Missing source"):
        join_release_boards(boards, unions, releases)
