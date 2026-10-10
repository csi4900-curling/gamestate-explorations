from copy import deepcopy
import json
from pathlib import Path

import pytest

from prototype.censored_event_state_handoff import (
    build_censored_event_state_handoff,
)


BASE = Path(__file__).resolve().parents[2] / "validation/throw-event-benchmark/canada-latvia-2024"


def inputs():
    return [
        json.loads((BASE / name).read_text())
        for name in (
            "end6-cross-resolution-body-cap-development.json",
            "full-right-area-end6-partial-state-development.json",
            "end6-field-of-view-censoring-development.json",
        )
    ]


def test_observed_tail_and_partial_board_do_not_become_physical_settle():
    rows = build_censored_event_state_handoff(*inputs())
    assert len(rows) == 20
    assert sum(row["observed_moving_pixels"] is not None for row in rows) == 16
    assert sum(row["following_partial_image_board"] is not None for row in rows) == 13
    assert (
        sum(
            row["terminal_visibility"] is not None
            and row["terminal_visibility"]["next_second_colour_screen"]["status"]
            == "unique_colour_component_provisional"
            for row in rows
        )
        == 15
    )
    assert all(
        row["physical_settle_time_s"] is None
        and row["same_stone_to_board_verified"] is False
        and row["simulation_ready"] is False
        for row in rows
    )
    witnessed = [
        row
        for row in rows
        if row["terminal_visibility"] is not None
        and row["terminal_visibility"]["selected_source_frame_boundary_contact_then_absence"]
    ]
    assert [row["right_proposal_id"] for row in witnessed] == ["R01:A401"]


def test_source_or_identity_mismatch_cannot_join():
    links, partial, boundary = inputs()
    bad = deepcopy(partial)
    bad["source_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="Source fingerprint"):
        build_censored_event_state_handoff(links, bad, boundary)
    bad = deepcopy(partial)
    bad["rows"][0]["colour_claim"] = "wrong"
    with pytest.raises(ValueError, match="Joined right proposal"):
        build_censored_event_state_handoff(links, bad, boundary)


def test_missing_terminal_evidence_cannot_silently_shrink_inventory():
    links, partial, boundary = inputs()
    bad = deepcopy(boundary)
    bad["paths"].pop()
    with pytest.raises(ValueError, match="Boundary coverage"):
        build_censored_event_state_handoff(links, partial, bad)
