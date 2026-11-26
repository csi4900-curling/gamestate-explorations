"""Product boundaries: source identity, saved settings, media seeking and reviews."""

from functools import partial
from http.server import ThreadingHTTPServer
import http.client
import json
from pathlib import Path
import threading

import cv2
import numpy as np
import pytest

from prototype.workbench import Workbench, Handler, write
from prototype.detection_cache import digest


def test_second_server_cannot_recover_active_job_store(tmp_path):
    from prototype.workbench import own_data_directory
    job=tmp_path/'jobs'/'active'/'job.json';job.parent.mkdir(parents=True)
    job.write_text(json.dumps({'state':'running'}))
    with own_data_directory(tmp_path):
        with pytest.raises(ValueError,match='Another workbench server owns'):
            with own_data_directory(tmp_path):
                Workbench(data=tmp_path)
        assert json.loads(job.read_text())['state']=='running'
    with own_data_directory(tmp_path):pass  # Lock releases on normal exit.


@pytest.fixture
def app(tmp_path):
    root = tmp_path
    config = root / "prototype/config"
    config.mkdir(parents=True)
    actual = Path(__file__).resolve().parents[1] / "config"
    for name in [
        "line-events-5hz.json",
        "bytetrack-5hz.yaml",
        "learned-directional-two-view-explicit-calibration.json",
        "stone-colour.example.json",
        "workbench.json",
    ]:
        (config / name).write_bytes((actual / name).read_bytes())
    (root / "prototype/component.py").write_text("VERSION = 1\n")
    (root / "prototype/calibration_ui.js").write_text("window.fixture = true;\n")
    video = root / "video.mp4"
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"mp4v"), 30, (64, 64))
    assert writer.isOpened()
    for i in range(30):
        writer.write(np.full((64, 64, 3), i * 3, dtype=np.uint8))
    writer.release()
    app = Workbench(root=root)
    app.profile["calibration_required"] = False
    yield app
    app.pool.shutdown(wait=True)


def imported(app):
    viewer = app.root / "previous"
    viewer.mkdir()
    (viewer / "index.html").write_text("<html>Existing viewer</html>")
    write(viewer / "manifest.json", {"source_sha256": digest(app.root / "video.mp4")})
    write(
        viewer / "states.json",
        {
            "summary": {"candidates": 2, "review_proposals": 1},
            "events": [
                {
                    "event_id": "A",
                    "crossing_time_s": 0.1,
                    "proposal": {"time_s": 0.2, "status": "review_proposal"},
                    "physical_revolutions": None,
                },
                {
                    "event_id": "B",
                    "crossing_time_s": 0.3,
                    "proposal": {"status": "unresolved"},
                    "physical_revolutions": None,
                },
            ],
        },
    )
    return app.import_result(viewer, app.root / "video.mp4")


def test_import_is_read_only_and_reviews_never_become_full_match_accuracy(app):
    job = imported(app)
    before = digest(app.root / "previous/states.json")
    app.review(job["id"], {"event_id": "A", "label": "throw", "reviewer": "human"})
    report = app.report(job["id"])
    assert report["review_summary"]["precision_on_reviewed_decidable_candidates"] == 1
    assert report["review_summary"]["recall"] is None
    assert report["physical_revolutions"] is None
    assert report["candidate_reviews"]["A"]["prediction_visible"]
    assert not report["candidate_reviews"]["A"]["independent_ground_truth"]
    assert digest(app.root / "previous/states.json") == before
    again = app.import_result(app.root / "previous", app.root / "video.mp4")
    assert again["id"] == job["id"]


def test_viewer_revision_changes_without_changing_observations_or_import_identity(app):
    job = imported(app)
    before = app.job(job["id"])
    state_hash = digest(app.root / "previous/states.json")
    (app.root / "previous/index.html").write_text("<html>Corrected orientation</html>")
    after = app.job(job["id"])
    assert before["board_url"] == after["board_url"]
    assert before["viewer_revisions"] != after["viewer_revisions"]
    assert digest(app.root / "previous/states.json") == state_hash
    assert app.import_result(app.root / "previous", app.root / "video.mp4")["id"] == job["id"]


def test_import_rejects_mismatched_trajectory_source_or_candidate_clock(app):
    job = imported(app)
    trajectory = app.root / "trajectory"
    trajectory.mkdir()
    (trajectory / "index.html").write_text("<html>Trajectory</html>")
    data = {
        "provenance": {"source_sha256": "different-source"},
        "events": [{"id": "A", "time_s": 0.1}, {"id": "B", "time_s": 0.3}],
    }

    def save():
        (trajectory / "rink-data.js").write_text("window.RINK_DATA=" + json.dumps(data) + ";\n")

    save()
    with pytest.raises(ValueError, match="different video"):
        app.import_result(app.root / "previous", app.root / "video.mp4", trajectory / "index.html")
    data["provenance"]["source_sha256"] = job["source_sha256"]
    data["events"][0]["time_s"] = 0.15
    save()
    with pytest.raises(ValueError, match="IDs/timestamps"):
        app.import_result(app.root / "previous", app.root / "video.mp4", trajectory / "index.html")
    data["events"][0]["time_s"] = 0.1
    save()
    result = app.import_result(
        app.root / "previous", app.root / "video.mp4", trajectory / "index.html"
    )
    assert result["import_evidence"]["candidate_id_times_match"]
    assert result["trajectory_url"].endswith("/trajectory/index.html")


def test_settings_are_saved_without_rewriting_shared_profile(app):
    asset = app.register_video(app.root / "video.mp4")
    original = digest(app.profile_path)
    identifier = app.prepare(
        {
            "video_id": asset["id"],
            "start_s": 0,
            "end_s": 0.8,
            "teams": ["RED TEAM", "YELLOW TEAM"],
            "line": [[0.1, 0.2], [0.4, 0.2]],
            "heights": {"body_box_center": 0.07},
            "dimensions": {"house_radius_m": 1.83},
        }
    )
    folder = app.data / "jobs" / identifier
    assert json.loads((folder / "state.json").read_text())["group_to_team"] == {
        "red": "RED TEAM",
        "yellow": "YELLOW TEAM",
    }
    assert (
        json.loads((folder / "match.json").read_text())["feature_heights_m"]["body_box_center"]
        == 0.07
    )
    assert json.loads((folder / "line.json").read_text())["lines"][0]["endpoints_normalized"] == [
        [0.1, 0.2],
        [0.4, 0.2],
    ]
    assert digest(app.profile_path) == original
    assert json.loads((folder / "spec.json").read_text())["source_sha256"] == asset["source_sha256"]
    (app.root / "prototype/component.py").write_text("VERSION = 2\n")
    assert (folder / "code/prototype/component.py").read_text() == "VERSION = 1\n"
    assert (folder / "code/prototype/calibration_ui.js").is_file()
    app.cancel(identifier)
    assert app.job(identifier)["state"] == "cancelled"


def test_invalid_input_and_reserved_source_cannot_start_inference(app):
    asset = app.register_video(app.root / "video.mp4")
    for request in [
        {"end_s": float("nan")},
        {"end_s": 99},
        {"line": [[0.1, 0.1], [0.1, 0.1]]},
        {"teams": ["A", "A"]},
    ]:
        with pytest.raises(ValueError):
            app.prepare({"video_id": asset["id"], **request})
    reserved = app.root / "validation/next-match-frozen-evaluation-2026-10-26"
    reserved.mkdir(parents=True)
    write(reserved / "selected-source.json", {"full_source_sha256": asset["source_sha256"]})
    with pytest.raises(ValueError, match="reserved"):
        app.register_video(app.root / "video.mp4")
    assert not app.jobs()


def test_restart_marks_unfinished_job_as_interrupted(app):
    asset = app.register_video(app.root / "video.mp4")
    identifier = app.prepare({"video_id": asset["id"]})
    restarted = Workbench(root=app.root)
    try:
        assert restarted.job(identifier)["state"] == "interrupted"
    finally:
        restarted.pool.shutdown(wait=True)


def test_changed_source_is_rejected_before_model_execution(app):
    asset = app.register_video(app.root / "video.mp4")
    identifier = app.prepare({"video_id": asset["id"]})
    with (app.root / "video.mp4").open("ab") as stream:
        stream.write(b"changed")
    app.execute(identifier)
    job = app.job(identifier)
    assert job["state"] == "failed"
    assert "Source video changed" in job["message"]
    assert not (app.data / "jobs" / identifier / "observations").exists()


@pytest.mark.parametrize('previous_state',['failed','done'])
def test_retry_reuses_only_complete_observations_and_preserves_failure(app, monkeypatch,previous_state):
    asset = app.register_video(app.root / "video.mp4")
    previous = app.prepare({"video_id": asset["id"], "start_s": 0, "end_s": 0.2})
    folder = app.data / "jobs" / previous
    observations = folder / "observations"
    observations.mkdir()
    events = {
        "status": "development_complete_event_stage",
        "source_fps": 30,
        "source_interval_s": [0, 0.2],
        "sample_step_frames": 3,
        "sampled_frames": 2,
        "source_sha256": asset["source_sha256"],
    }
    write(observations / "events.json", events)
    rows = "".join(
        json.dumps({"frame_index": frame, "time_s": frame / 30}) + "\n" for frame in [0, 3]
    )
    for name in ["observations.jsonl", "match-observations.jsonl", "score-observations.jsonl"]:
        (observations / name).write_text(rows)
    app.update(previous, state=previous_state, message="Existing output preserved")
    before = digest(observations / "observations.jsonl")
    submitted = []
    monkeypatch.setattr(
        app, "schedule", lambda identifier: submitted.append(identifier)
    )
    action=app.rebuild_outputs if previous_state=='done' else app.retry
    retry = action(previous)
    assert submitted == [retry["id"]]
    spec = json.loads((app.data / "jobs" / retry["id"] / "spec.json").read_text())
    assert spec["reused_observations_from"] == previous
    assert spec["reused_scan_verification"]["verified_sampled_frames"] == 2
    assert digest(app.data / "jobs" / retry["id"] / "observations/observations.jsonl") == before
    assert app.job(previous)["state"] == previous_state
    assert digest(observations / "observations.jsonl") == before
    (observations / "observations.jsonl").write_text(rows.splitlines()[0] + "\n")
    count = len(app.jobs())
    with pytest.raises(ValueError, match="Incomplete scan"):
        action(previous)
    assert len(app.jobs()) == count


def test_worker_failure_is_visible_even_when_storage_cannot_save_status(app,monkeypatch):
    asset=app.register_video(app.root/'video.mp4')
    identifier=app.prepare({'video_id':asset['id'],'start_s':0,'end_s':.2})
    update=app.update
    def quota(*args,**kwargs):raise OSError(122,'Disk quota exceeded')
    monkeypatch.setattr(app,'execute',quota)
    monkeypatch.setattr(app,'update',quota)
    future=app.schedule(identifier)
    with pytest.raises(OSError,match='quota'):future.result()
    app.pool.shutdown(wait=True)
    live=app.job(identifier)
    assert live['state']=='failed' and 'Disk quota exceeded' in live['message']
    assert json.loads((app.data/'jobs'/identifier/'job.json').read_text())['state']=='queued'
    monkeypatch.setattr(app,'update',update)
    assert app.job(identifier)['state']=='failed'
    assert json.loads((app.data/'jobs'/identifier/'job.json').read_text())['state']=='failed'
    assert identifier not in app.runtime_failures


def test_http_media_ranges_and_review_round_trip(app):
    job = imported(app)

    class Quiet(Handler):
        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, app=app))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def request(method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = (response.status, response.read())
        connection.close()
        return result

    try:
        status, data = request("GET", "/media/" + job["video_id"], headers={"Range": "bytes=2-9"})
        assert status == 206 and data == (app.root / "video.mp4").read_bytes()[2:10]
        status, data = request(
            "POST",
            "/api/jobs/" + job["id"] + "/review",
            json.dumps({"event_id": "B", "label": "false_detection"}),
            {"Content-Type": "application/json"},
        )
        assert status == 200 and json.loads(data)["B"]["label"] == "false_detection"
        status, data = request("GET", "/api/jobs/" + job["id"] + "/report")
        assert status == 200
        assert json.loads(data)["review_summary"]["reviewed_false_detections"] == 1
        assert request("GET", "/files/../../etc/passwd")[0] == 404
        assert request("GET", "/")[0] == 200
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_viewer_data_update_changes_revision_and_served_script_without_mutating_html(app):
    job = imported(app)
    html = app.root/'previous/index.html'
    html.write_text('<script src="states.js"></script>')
    data = html.with_name('states.js')
    data.write_text('window.POST_THROW={};')
    before = app.job(job['id'])['viewer_revisions']['board_url']
    original = html.read_bytes()
    served_before = app.viewer_html(html)
    data.write_text('window.POST_THROW={score_tracking:{timeline:[]}};')
    after = app.job(job['id'])['viewer_revisions']['board_url']
    served_after = app.viewer_html(html)
    assert before != after
    assert served_before != served_after
    assert b'states.js?data=' in served_after
    assert html.read_bytes() == original


def test_event_api_exposes_post_throw_points_and_keeps_missing_results_unknown(app):
    job = imported(app)
    path = app.root/'previous/states.json'
    payload = json.loads(path.read_text())
    payload['detected_throw_scoring'] = {'history': [
        {'event_id': 'A', 'estimated_points': {'A': 2, 'B': 0},
         'status': 'estimated_with_last_known_positions'}]}
    write(path, payload)
    first, missing = app.events(job['id'])
    assert first['post_throw_points'] == {'A': 2, 'B': 0}
    assert first['proposal_time_s'] == .2
    assert missing['proposal_time_s'] is None
    assert missing['post_throw_points'] is None


def test_register_video_normalizes_pasted_paths_and_lists_known_videos(app):
    import shutil
    video_path = app.root / "video.mp4"
    upload_copy = app.data / "uploads" / "dup-video.mp4"
    shutil.copyfile(video_path, upload_copy)

    # Register upload copy first, then canonical path via quoted/spaced/file:// inputs.
    app.register_video(upload_copy)
    for raw in [
        f"  {video_path}\n",
        f'"{video_path}"',
        f"'{video_path}'",
        f"`{video_path}`",
        f"file://{video_path}",
        str(app.root),
    ]:
        reg = app.register_video(raw)
        assert reg["path"] == str(video_path.resolve())

    job = app.prepare({"video_id": reg["id"]})
    app.update(job, name="Canonical Match")

    listed = app.defaults()["videos"]
    assert len(listed) == 1
    assert listed[0]["path"] == str(video_path.resolve())
    assert listed[0]["label"].startswith("Canonical Match · ")

    preferred_dir = app.root / "match_dir"
    preferred_dir.mkdir()
    shutil.copyfile(video_path, preferred_dir / "other.mp4")
    shutil.copyfile(video_path, preferred_dir / "source-1080p.mp4")
    assert app.register_video(str(preferred_dir))["path"] == str((preferred_dir / "source-1080p.mp4").resolve())
    with pytest.raises(ValueError, match="Enter a video path"):
        app.register_video("   ")


def test_sidebar_job_list_matches_full_job_rows_and_tracks_updates(app):
    asset = app.register_video(app.root / "video.mp4")
    identifier = app.prepare({"video_id": asset["id"]})
    [row] = app.job_list()
    full = app.job(identifier)
    for key in ("id", "name", "state", "start_s", "end_s", "source_sha256",
                "has_completed_detector_scan", "committed_detector_prefix"):
        assert row[key] == full[key]
    app.update(identifier, state="failed", message="changed")
    assert app.job_list()[0]["state"] == "failed"
