from hashlib import sha256

import numpy as np
import pytest

from prototype import layout_camera_motion as router


def preflight(layout="split_2024", *, runs=None):
    return {
        "source_sha256": "source-hash",
        "preflight_sha256": sha256(router.LAYOUT_CODE.read_bytes()).hexdigest(),
        "source_interval_s": [0, 20],
        "runs": runs or [{"layout": layout, "interval_s": [0, 20], "samples": 8}],
    }


def test_split_routing_preserves_panel_coordinates(monkeypatch):
    seen = {}

    def fake_pair(p0, p1, t0, t1, frame_at):
        seen["shape"] = frame_at(t0).shape
        seen["points"] = (p0, p1)
        return {"status": "registered", "camera_residual_px": 12, "subpairs": []}

    monkeypatch.setattr(router, "camera_relative_pair", fake_pair)
    frame = np.zeros((1080, 1920, 3), np.uint8)
    result = router.source_camera_relative_pair(
        preflight(), "source-hash", (1260, 600), (1290, 570), 2, 3, lambda _: frame
    )
    assert result["panel"] == "right"
    assert result["coordinate_frame"] == "640x720_aspect_preserved_panel_pixels"
    assert seen["shape"] == (720, 640, 3)
    assert seen["points"] == ((200.0, 400.0), (220.0, 380.0))


def test_2022_and_2024_lowres_use_distinct_registration(monkeypatch):
    called = []

    def fake_ice(p0, p1, t0, t1, frame_at):
        called.append(frame_at(t0).shape)
        return {"status": "registered", "camera_residual_px": 4, "subpairs": []}

    monkeypatch.setattr(router, "ice_region_composed_residual", fake_ice)
    frame = np.zeros((360, 640, 3), np.uint8)
    accepted = router.source_camera_relative_pair(
        preflight("beijing_2022"), "source-hash", (100, 200), (105, 180), 2, 3, lambda _: frame
    )
    assert accepted["camera_residual_px"] == 4
    assert called == [(360, 640, 3)]
    monkeypatch.setattr(
        router.lowres_split,
        "source_pair",
        lambda *args: {
            "status": "registered",
            "camera_residual_px": 9,
            "panel": "left",
            "coordinate_frame": "640x720_upsampled_360p_split_panel_pixels",
            "subpairs": [],
        },
    )
    routed = router.source_camera_relative_pair(
        preflight(), "source-hash", (100, 200), (105, 180), 2, 3, lambda _: frame
    )
    assert routed["camera_residual_px"] == 9
    assert routed["coordinate_frame"] == "640x720_upsampled_360p_split_panel_pixels"
    assert routed["layout"] == "split_2024"
    assert called == [(360, 640, 3)]


def test_boundary_unknown_and_cross_panel_abstain_without_registration():
    runs = [
        {"layout": "split_2024", "interval_s": [0, 10], "samples": 8},
        {"layout": "unknown", "interval_s": [10, 20], "samples": 8},
    ]
    frame = np.zeros((1080, 1920, 3), np.uint8)
    at = lambda _: frame
    assert (
        router.source_camera_relative_pair(
            preflight(runs=runs), "source-hash", (100, 200), (110, 210), 9, 11, at
        )["status"]
        == "crosses_layout_run_boundary"
    )
    assert (
        router.source_camera_relative_pair(
            preflight(runs=runs), "source-hash", (100, 200), (110, 210), 11, 12, at
        )["status"]
        == "unsupported_layout_run"
    )
    assert (
        router.source_camera_relative_pair(
            preflight(), "source-hash", (900, 200), (1000, 210), 2, 3, at
        )["status"]
        == "crosses_split_panel_boundary"
    )
    lowres = np.zeros((360, 640, 3), np.uint8)
    assert (
        router.source_camera_relative_pair(
            preflight(), "source-hash", (310, 200), (330, 210), 2, 3, lambda _: lowres
        )["status"]
        == "crosses_split_panel_boundary"
    )


def test_mismatched_preflight_fails_closed():
    with pytest.raises(ValueError, match="Preflight source"):
        router.source_camera_relative_pair(
            preflight(),
            "different-video",
            (100, 200),
            (110, 210),
            2,
            3,
            lambda _: np.zeros((1080, 1920, 3), np.uint8),
        )
