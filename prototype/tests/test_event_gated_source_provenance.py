import json

import pytest

from prototype.scripts import scan_china_event_gated_boards as china
from prototype.scripts import scan_norway_end2_event_gated_boards as norway
from prototype.scripts import export_event_gated_video_states as export


@pytest.mark.parametrize("scanner", [china, norway])
def test_event_gate_rejects_review_from_another_recording(tmp_path, monkeypatch, scanner):
    review = tmp_path / "wrong-review.json"
    counter = tmp_path / "counter.json"
    if scanner is china:
        review.write_text(json.dumps({"games": [{"official_game_code": "PREL000102",
                                                "source_sha256": "wrong",
                                                "segments": []}]}))
    else:
        review.write_text(json.dumps({"source_sha256": "wrong", "events": []}))
    counter.write_text(json.dumps({"source_sha256": "correct", "counter_events": []}))
    monkeypatch.setattr(scanner, "REVIEW", review)
    monkeypatch.setattr(scanner, "COUNTERS", counter)
    monkeypatch.setattr(scanner, "digest", lambda path: "correct")
    with pytest.raises(ValueError, match="source|Source"):
        scanner.build()


def test_state_export_rejects_different_norway_review(tmp_path, monkeypatch):
    review = tmp_path / "wrong-norway-review.json"
    review.write_text(json.dumps({"source_sha256": "wrong", "events": []}))
    monkeypatch.setattr(export, "NORWAY_REVIEW", review)
    with pytest.raises(ValueError, match="provenance"):
        export.build()
