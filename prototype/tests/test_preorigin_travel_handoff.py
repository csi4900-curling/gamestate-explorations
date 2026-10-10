"""Integration checks for the additive B02 handoff."""

import json
from pathlib import Path

from prototype.scripts.export_pwg2022_event_evidence_handoff_v3 import build


ROOT = Path(__file__).resolve().parents[2]


def test_b02_is_travel_only_and_all_v2_records_are_preserved():
    v2 = json.loads((ROOT / "validation/official-shot-sequence/"
                     "pwg2022-event-evidence-handoff-v2-development.json").read_text())
    v3 = build()
    old = {row["event_id"]: row for game in v2["games"] for row in game["rows"]}
    new = {row["event_id"]: row for game in v3["games"] for row in game["rows"]}
    assert len(new) == len(old) + 1
    assert all(new[event_id] == row for event_id, row in old.items())
    b02 = new["TRAVEL-B02"]
    assert b02["receiving_view"]["motion_interval_s"] == [365.4, 380.2]
    assert b02["release_cue"]["time_s"] is None
    assert b02["physical_release_time_s"] is None
    assert b02["persistent_stone_id"] is None
    assert b02["simulation_ready"] is False
