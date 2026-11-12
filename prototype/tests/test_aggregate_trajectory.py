"""Failure propagation and real-video integration checks for aggregate outputs."""

import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aggregate_trajectory import bounded_segments, sample_segment, summarize
from cache_contract import file_sha256
from scripts.complete_throw_trajectories import complete, project_sample


def point(t, x=10):
    return {"time_s": t, "pixel": [x, 100]}


def test_stale_identity_gaps_and_jumps_do_not_become_one_path():
    segments, reasons = bounded_segments([point(0), point(1), point(5), point(5.1, 100), point(31)])
    assert [len(s) for s in segments] == [2, 1, 1]
    assert set(reasons) == {
        "continuation_exceeds_30s_identity_horizon",
        "observation_gap",
        "pixel_identity_jump",
    }
    with pytest.raises(ValueError, match="strictly increase"):
        bounded_segments([point(1), point(1)])


def test_sampling_keeps_last_point_and_rejects_bad_rate():
    assert [
        p["time_s"] for p in sample_segment([point(0), point(0.1), point(0.5), point(0.7)])
    ] == [0, 0.5, 0.7]
    with pytest.raises(ValueError):
        sample_segment([], 0)


def test_funnel_never_counts_isolated_projection_or_drops_failures():
    events = [
        {"segments": []},
        {
            "segments": [
                {
                    "pixel_points": [point(0), point(1)],
                    "geometry_samples": [
                        {"top_view_m": [0, 0]},
                        {"top_view_m": None},
                        {"top_view_m": [0, 1]},
                    ],
                }
            ]
        },
    ]
    result = summarize(events)
    assert result["event_candidates"] == 2
    assert result["events_with_pixel_segment"] == 1
    assert result["events_with_image_supported_top_view_segment"] == 0


def test_registration_failure_cannot_leak_stale_homography():
    class RejectingCalibrator:
        def register(self, frame):
            return None, {"status": "rejected"}

    result = project_sample(np.zeros((360, 640, 3), np.uint8), point(0), RejectingCalibrator(), {})
    assert result["top_view_m"] is None
    assert result["homography_source_pixels_to_local_metres"] is None


def test_real_video_preserves_failed_events_and_validates_source_and_cache(tmp_path):
    video = tmp_path / "source.avi"
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), 10, (640, 360))
    assert writer.isOpened()
    for _ in range(20):
        writer.write(np.full((360, 640, 3), 180, np.uint8))
    writer.release()
    events = tmp_path / "events.json"
    doc = {
        "source_sha256": file_sha256(video),
        "source_interval_s": [0, 2],
        "events": [
            {"id": "one", "colour": "yellow", "observed_track_points": [point(0), point(1)]},
            {"id": "two", "observed_track_points": []},
        ],
    }
    events.write_text(json.dumps(doc))
    output = tmp_path / "aggregate.json"
    result = complete(video, events, output, integrated=False)
    assert result["summary"]["event_candidates"] == 2
    assert result["summary"]["events_with_image_supported_top_view_segment"] == 0
    assert (
        result["events"][0]["segments"][0]["geometry_samples"][0]["status"] == "registration_failed"
    )
    assert complete(video, events, output, integrated=False) == result
    doc["events"][0]["colour"] = "red"
    events.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="cache context"):
        complete(video, events, output, integrated=False)
    doc["source_sha256"] = "wrong"
    events.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="fingerprints"):
        complete(video, events, output, integrated=False)


@pytest.mark.parametrize(
    "rings_pass,x,status",
    [
        (True, 10, "image_supported_ice_plane_projection"),
        (False, 10, "ring_geometry_failed"),
        (True, 100, "outside_nominal_rink_bounds"),
    ],
)
def test_projection_scales_source_pixels_and_enforces_ring_and_bounds_gates(
    monkeypatch, rings_pass, x, status
):
    from scripts import complete_throw_trajectories as module

    class FixedCalibrator:
        def register(self, frame):
            assert frame.shape[:2] == (1080, 1920)
            return np.diag([0.01, 0.001, 1.0]), {"status": "accepted"}

    monkeypatch.setattr(module, "validate_rings", lambda *args: (rings_pass, {}))
    result = project_sample(
        np.zeros((360, 640, 3), np.uint8), point(0, x), FixedCalibrator(), {"region": []}
    )
    assert result["status"] == status
    if status == "image_supported_ice_plane_projection":
        assert result["top_view_m"] == pytest.approx([0.3, 0.3])
        assert np.asarray(result["homography_source_pixels_to_local_metres"]) == pytest.approx(
            np.diag([0.03, 0.003, 1.0])
        )
    else:
        assert result["top_view_m"] is None
        assert result["homography_source_pixels_to_local_metres"] is None
