import json
import sys
from pathlib import Path
import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from automatic_house_calibration import calibrate_house
from integrated_trajectory import assess_track, link_segments
from scripts.audit_full_shot_cap_motion import tracks_for_shot
from scripts.run_throw_pipeline import run_adapter


def test_automatic_calibration_on_projected_rings_and_blank_rejection():
    frame = np.full((360, 640, 3), 235, np.uint8)
    for r, c in [
        (130, (200, 70, 10)),
        (130 * 1.219 / 1.829, (235, 235, 235)),
        (130 * 0.610 / 1.829, (20, 20, 210)),
    ]:
        cv2.ellipse(frame, (320, 210), (round(r), round(r * 0.65)), 0, 0, 360, c, -1)
    H, d = calibrate_house(frame)
    assert H is not None
    from vision_core import project

    assert project(H, [[320, 210]])[0] == pytest.approx([0, 0], abs=0.04)
    assert np.linalg.norm(project(H, [[450, 210]])[0]) == pytest.approx(1.829, abs=0.04)
    assert d["withheld_inner"]["p95_abs_radial_error_m"] < 0.15
    assert calibrate_house(np.full_like(frame, 235))[0] is None


def test_motion_exports_preserve_coordinates_for_both_channels():
    points = [
        (t, [{"pixel": [100 + t * 10, 100], "bbox": [95 + t * 10, 95, 10, 10]}]) for t in range(5)
    ]
    result = tracks_for_shot({"red": points, "yellow": []}, "S01")
    assert len(result) == 1
    assert [p["time_s"] for p in result[0]["points"]] == list(range(5))


def test_track_identity_requires_learned_support_scale_and_motion():
    track = {
        "points": [
            {
                "time_s": t,
                "pixel": [10 + t, 10],
                "bbox": [10 + t, 10, 10, 10],
                "channels": ["learned", "cap"],
            }
            for t in range(4)
        ]
    }
    samples = [
        {
            "time_s": t,
            "top_view_m": [t * 0.2, 0],
            "homography_source_pixels_to_local_metres": np.diag([0.02, 0.02, 1]).tolist(),
        }
        for t in range(4)
    ]
    assert json.loads(json.dumps(assess_track(track, samples)))["eligible"]
    for p in track["points"]:
        p["channels"] = ["cap"]
    assert not assess_track(track, samples)["eligible"]
    for p in track["points"]:
        p["channels"] = ["learned"]
        p["bbox"][2] = 100
    assert not assess_track(track, samples)["eligible"]


def test_links_do_not_force_ambiguous_or_backward_connections():
    def segment(key, role, t, y):
        return {
            "segment_id": key,
            "role": role,
            "associated": True,
            "colour": "red",
            "geometry_samples": [{"time_s": t, "rink_position_m": [0, y]}],
        }

    a = segment("a", "departure", 1, 25)
    b = segment("b", "receiving", 3, 28)
    b["geometry_samples"].append({"time_s": 4, "rink_position_m": [0, 30]})
    assert len(link_segments([a, b])) == 1
    c = {**b, "segment_id": "c"}
    assert not link_segments([a, b, c])
    assert not link_segments([a, segment("static", "receiving", 3, 29)])
    assert not link_segments([a, segment("d", "receiving", 0, 15)])


def test_beijing_router_uses_full_shot_and_preserves_manifest(tmp_path, monkeypatch):
    from scripts import run_throw_pipeline as runner

    called = []

    def child(script, *args):
        called.append(script)
        out = tmp_path / "full-shot"
        out.mkdir()
        (out / "candidate-event-ledger.json").write_text(
            json.dumps(
                {
                    "source_sha256": "test",
                    "source_interval_s": [0, 10],
                    "events": [
                        {"candidate_id": "T001", "observation_anchor_s": 4, "shot_id": "S01"}
                    ],
                }
            )
        )

    monkeypatch.setattr(runner, "run_child", child)
    path, result = run_adapter(Path("video"), "v", "test", "beijing_2022", 0, 10, tmp_path)
    assert called == ["run_full_shot_evidence.py"]
    assert result["source_id"] == "v"
    assert result["events"][0]["crossing_time_s"] == 4
    assert result["events"][0]["motion_review_path"].endswith("shot-review/manifest.json")


def test_track_claimed_by_two_events_is_not_counted_twice():
    from copy import deepcopy
    from integrated_trajectory import reject_reused_tracks

    s = {
        "camera": "S01",
        "colour": "red",
        "role": "receiving",
        "associated": True,
        "pixel_points": [{"time_s": t, "pixel": [t, 10]} for t in range(5)],
        "geometry_samples": [],
    }
    events = [
        {
            "candidate_id": key,
            "segments": [{**deepcopy(s), "segment_id": key + ":0"}],
            "failure_reasons": [],
            "cross_view_links": [],
        }
        for key in ("a", "b")
    ]
    reject_reused_tracks(events)
    assert all(not e["segments"] for e in events)
    assert all(e["failure_reasons"] == ["track_claimed_by_multiple_events"] for e in events)
    assert all(len(e["unassigned_segments"]) == 1 for e in events)


@pytest.mark.parametrize('direction', [-1, 1])
def test_common_rink_display_rotates_image_axes_without_reflection(direction):
    from integrated_trajectory import orient_image_aligned_samples

    # A non-collinear triangle, with longitudinal movement in either direction.
    points = [{'top_view_m': xy} for xy in [[0., 0.], [1., 0.], [1., direction * 2.]]]
    orient_image_aligned_samples(points, 'receiving')
    source = np.array([p['top_view_m'] for p in points])
    display = np.array([[p['rink_position_m'][0], -p['rink_position_m'][1]] for p in points])
    assert np.linalg.det(source[1:] - source[0]) * np.linalg.det(display[1:] - display[0]) > 0
    assert display[-1, 1] < display[0, 1]


def test_t002_overhead_below_right_rotates_to_above_left():
    from integrated_trajectory import orient_image_aligned_samples

    points = [{'top_view_m': xy} for xy in [[.8646, -.5575], [1.1509, .7943]]]
    orient_image_aligned_samples(points, 'receiving')
    assert points[-1]['rink_position_m'] == pytest.approx([-1.1509, 35.5413])
