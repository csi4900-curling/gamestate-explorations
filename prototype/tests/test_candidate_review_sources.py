"""Archived raw/confirmed runs can supply lossless review triage."""

import json
from pathlib import Path
import tempfile

import pytest

from scripts.export_candidate_review_union import load_left_sources


def fixture(folder):
    run_dir = folder / "run-01"
    run_dir.mkdir()
    raw = {"source_sha256": "source", "source_interval_s": [0, 100],
           "events": [{"id": "S01", "colour": "red", "crossing_time_s": 10,
                       "first_observed_s": 9, "confirmed_at_s": 11},
                      {"id": "S02", "colour": "yellow", "crossing_time_s": 20,
                       "first_observed_s": 19, "confirmed_at_s": 21}]}
    confirmed = {"source_sha256": "source", "source_interval_s": [0, 100],
                 "events": [{"id": "S01", "colour": "red", "crossing_time_s": 10}],
                 "withheld_events": [{"id": "S02"}]}
    (run_dir / "raw.json").write_text(json.dumps(raw) + "\n")
    (run_dir / "events.json").write_text(json.dumps(confirmed) + "\n")
    timeline = {"source_sha256": "source", "supported_runs": [
        {"id": "R01", "layout": "split_2024", "interval_s": [0, 100],
         "adapter_artifact": "run-01/events.json"}]}
    return folder / "timeline.json", timeline


def test_missing_saved_triage_reconstructed_from_same_raw_and_confirmation():
    with tempfile.TemporaryDirectory() as directory:
        path, timeline = fixture(Path(directory))
        proposals, saved, reconstructed, raw_hashes = load_left_sources(path, timeline)
        assert saved == {}
        assert list(reconstructed) == ["R01"]
        assert list(raw_hashes) == ["R01"]
        assert [p["disposition"] for p in proposals["R01"]] == [
            "auto_confirmed_candidate", "needs_review"]
        assert proposals["R01"][0]["observed_motion_interval_s"] == [9, 11]


def test_reconstruction_rejects_source_mismatch():
    with tempfile.TemporaryDirectory() as directory:
        path, timeline = fixture(Path(directory))
        timeline["source_sha256"] = "other"
        with pytest.raises(ValueError, match="source differ"):
            load_left_sources(path, timeline)
