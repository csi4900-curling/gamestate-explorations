from hashlib import sha256

import numpy as np

from prototype import candidate_camera_motion as cue
from prototype import layout_camera_motion as router


def preflight():
    return {
        "source_sha256": "source",
        "preflight_sha256": sha256(router.LAYOUT_CODE.read_bytes()).hexdigest(),
        "source_interval_s": [0, 20],
        "runs": [{"layout": "split_2024", "interval_s": [0, 20]}],
    }


def event():
    return {
        "id": "S01",
        "observed_track_points": [
            {"time_s": 2.0, "pixel": [150, 60]},
            {"time_s": 2.5, "pixel": [151, 50]},
        ],
    }


def test_1080p_candidate_points_scale_to_source_before_routing(monkeypatch):
    seen = {}

    def fake_route(pre, digest, p0, p1, t0, t1, frame_at):
        seen["points"] = (p0, p1)
        return {"status": "registered", "camera_residual_px": 15}

    monkeypatch.setattr(cue, "source_camera_relative_pair", fake_route)
    row = cue.measure_candidate(
        event(), preflight(), "source", lambda _: np.zeros((1080, 1920, 3), np.uint8)
    )
    assert seen["points"] == ([450.0, 180.0], [453.0, 150.0])
    assert row["camera_residual_px"] == 15


def test_missing_path_abstains():
    row = cue.measure_candidate({"id": "S01"}, preflight(), "source", lambda _: None)
    assert row["status"] == "no_observed_track_path"
    assert row["camera_residual_px"] is None
