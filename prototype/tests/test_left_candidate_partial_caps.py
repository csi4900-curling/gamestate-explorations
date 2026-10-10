"""Left candidate board samples must respect other proposals and timing uncertainty."""

from scripts import export_left_candidate_partial_caps as scan


def fixtures():
    union = {
        "source_sha256": "source",
        "candidates": [
            {
                "candidate_id": "R01-S1",
                "origin": "left_routed_proposal",
                "source_run_id": "R01",
                "source_time_s": 10,
                "observed_motion_interval_s": [9, 11],
            },
            {
                "candidate_id": "R01-S2",
                "origin": "left_routed_proposal",
                "source_run_id": "R01",
                "source_time_s": 50,
                "observed_motion_interval_s": [49, 51],
            },
        ],
    }
    timeline = {
        "source_sha256": "source",
        "supported_runs": [
            {"id": "R01", "layout": "split_2024", "interval_s": [0, 100]},
        ],
    }
    return union, timeline


def test_guard_blocks_next_candidate_and_route_boundary():
    union, timeline = fixtures()
    assert (
        scan.guard_tail(union["candidates"][0], 30, 100, 100)
        == "abstain_next_candidate_or_route_boundary"
    )
    assert (
        scan.guard_tail(union["candidates"][0], 50, 32, 100)
        == "abstain_next_candidate_or_route_boundary"
    )
    assert scan.guard_tail(union["candidates"][0], 50, 100, 100) is None


def test_sampler_keeps_withheld_candidate_and_abstains_on_uncertain_anchor(monkeypatch):
    union, timeline = fixtures()
    union["candidates"][0]["review_status"] = "left_context_withheld_review"

    def fake_observe(_cap, _fps, _duration, anchor):
        status = (
            "partial_stable_colour_cap_proposals"
            if anchor == 10
            else "no_stable_colour_cap_proposals"
        )
        return {
            "anchor_time_s": anchor,
            "observation_status": status,
            "sample_frames": [{"time_s": anchor + 15}],
            "stable_cap_proposals": [],
        }

    monkeypatch.setattr(scan, "observe_anchor", fake_observe)
    rows = scan.export_observations(None, 30, 100, union, timeline)
    assert len(rows) == 2
    assert rows[0]["candidate_id"] == "R01-S1"
    assert rows[0]["observation_status"] == "abstain_motion_time_sensitive"
    assert rows[0]["stable_cap_proposals"] == []


def test_right_entry_between_left_candidates_blocks_tail():
    union, timeline = fixtures()
    union["candidates"].insert(
        1, {"candidate_id": "RIGHT-I01:R1", "origin": "right_entry_review", "source_time_s": 30}
    )
    union["candidates"][2]["observed_motion_interval_s"] = None
    rows = scan.export_observations(None, 30, 100, union, timeline)
    assert rows[0]["observation_status"] == "abstain_next_candidate_or_route_boundary"
