"""Local product workbench for the shared left/right curling pipeline.

Launch: feasibility/scripts/python.sh -m prototype.workbench
Jobs and reviews persist; existing research artifacts are imported read-only.
"""

import argparse
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import hashlib
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time
from urllib.parse import parse_qs, unquote, urlsplit
import uuid

from prototype.detection_cache import digest
from prototype.server import Handler as VideoHandler

ROOT = Path(__file__).resolve().parents[1]
WEB = Path(__file__).with_name("workbench.html")


def write(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def _calibrated_hog_line_normalized(calibration_assets, panel="left", hog_y_m=-6.401, half_width_m=2.375):
    """Project the calibrated hog line endpoints into [0, 1] source-image fractions."""
    import numpy as np
    for asset in calibration_assets or []:
        rec = (asset.get("panels") or {}).get(panel)
        if not rec or not rec.get("H_normalized_source_to_local_m"):
            continue
        try:
            H = np.asarray(rec["H_normalized_source_to_local_m"], dtype=float)
            Hinv = np.linalg.inv(H)
            pts = []
            for x_m in (-half_width_m, half_width_m):
                v = Hinv @ np.array([x_m, hog_y_m, 1.0], dtype=float)
                if abs(v[2]) < 1e-12:
                    raise ValueError("singular")
                pts.append([
                    float(min(1.0, max(0.0, (v[0] / v[2]) / 640.0))),
                    float(min(1.0, max(0.0, (v[1] / v[2]) / 360.0))),
                ])
            if pts[0] != pts[1]:
                return pts
        except Exception:
            continue
    return None


def finite(value, name, low=None):
    value = float(value)
    if not math.isfinite(value) or (low is not None and value < low):
        raise ValueError("Invalid " + name)
    return value


@contextmanager
def own_data_directory(data):
    """Only one server may recover and mutate a job store at a time."""
    import fcntl
    data=Path(data).resolve();data.mkdir(parents=True,exist_ok=True)
    with (data/'.server.lock').open('a+') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Another workbench server owns this data directory; use its existing URL') from None
        try:yield
        finally:fcntl.flock(lock,fcntl.LOCK_UN)


class Workbench:
    def __init__(self, root=ROOT, data=None, profile=None, external_jobs=()):
        self.root = Path(root).resolve()
        self.data = Path(data or self.root / "workbench-data").resolve()
        self.data.mkdir(parents=True, exist_ok=True)
        for name in ["videos", "jobs", "uploads"]:
            (self.data / name).mkdir(exist_ok=True)
        self.profile_path = Path(profile or self.root / "prototype/config/workbench.json").resolve()
        self.profile = json.loads(self.profile_path.read_text())
        from prototype.calibration_store import CalibrationStore
        self.calibrations = CalibrationStore(self)
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.lock = threading.RLock()
        self.processes = {}
        self.cancelled = set()
        self.history_lock = threading.Lock()
        self.history_cache = {}
        self.runtime_failures = {}
        self.external_jobs = {self.identifier(job) for job in external_jobs}
        for p in (self.data / "jobs").glob("*/job.json"):
            row = json.loads(p.read_text())
            if row["state"] in ["running", "queued"] and row["id"] not in self.external_jobs:
                row.update(
                    state="interrupted",
                    message="Application restarted. Existing outputs preserved; create a new run to process again.",
                )
                write(p, row)

    def path(self, value):
        p = Path(value)
        return (self.root / p).resolve() if not p.is_absolute() else p.resolve()

    def identifier(self, value):
        if not re.fullmatch(r"[a-f0-9]{12}", value):
            raise ValueError("Invalid identifier")
        return value

    def video(self, identifier):
        return json.loads(
            (self.data / "videos" / (self.identifier(identifier) + ".json")).read_text()
        )

    def job(self, identifier):
        result = json.loads(
            (self.data / "jobs" / self.identifier(identifier) / "job.json").read_text()
        )
        failure=self.runtime_failures.get(identifier)
        if failure:
            result.update(failure)
            try:
                self.update(identifier,**failure)
                self.runtime_failures.pop(identifier,None)
            except OSError:pass  # Keep the live API truthful while storage is unavailable.
        result["externally_managed"] = identifier in self.external_jobs and result["state"] in ("queued", "running")
        result["reviews"] = self.reviews(identifier)
        from prototype.review_presentation import focused_views
        result=focused_views(self,result)
        # Viewer HTML can be repaired without rerunning immutable observations.
        # Give the browser a new URL when that presentation changes.
        throws = self.data / "jobs" / identifier / "result/throws/index.html"
        if throws.exists():
            result["throw_url"] = self.file_url(throws)
        result["viewer_revisions"] = {}
        for key in ("board_url", "trajectory_url", "throw_url"):
            url = result.get(key)
            if url and url.startswith("/files/"):
                path = (self.root / unquote(urlsplit(url).path[len("/files/"):])).resolve()
                if path.is_relative_to(self.root) and path.is_file():
                    assets = [path, path.with_name("states.js"), path.with_name("rink-data.js"), path.with_name("effects.js")]
                    fingerprint = "".join(digest(asset) for asset in assets if asset.is_file())
                    result["viewer_revisions"][key] = hashlib.sha256(fingerprint.encode()).hexdigest()[:16]
        events_path = self.data / "jobs" / identifier / "observations/events.json"
        result['has_completed_detector_scan'] = False
        if events_path.exists():
            try:result['has_completed_detector_scan'] = json.loads(events_path.read_text()).get('status') == 'development_complete_event_stage'
            except json.JSONDecodeError:pass
        result['committed_detector_prefix'] = None
        if result['state'] in ['failed','interrupted','cancelled'] and not result['has_completed_detector_scan']:
            try:
                from prototype.detection_cache import verify_committed_prefix
                result['committed_detector_prefix']=verify_committed_prefix(events_path.parent)
            except (OSError,ValueError,KeyError,TypeError):pass
        result["can_retry"] = (
            result["state"] in ["failed", "interrupted", "cancelled"] and events_path.exists()
        )
        result['can_rebuild_outputs'] = result['state']=='done' and result['has_completed_detector_scan'] and not result.get('imported')
        progress = self.data / "jobs" / identifier / "observations/progress.json"
        if result["state"] == "running" and progress.exists():
            try:
                result["observation_progress"] = json.loads(progress.read_text())
            except json.JSONDecodeError:
                pass
        return result

    def jobs(self):
        return sorted(
            [self.job(p.parent.name) for p in (self.data / "jobs").glob("*/job.json")],
            key=lambda x: x["created_at"],
            reverse=True,
        )

    def viewer_html(self, path):
        """Serve coherent HTML/data versions without mutating saved experiments."""
        path = Path(path)
        def version(match):
            asset = path.with_name(match[2])
            if not asset.is_file():
                return match[0]
            return 'src=' + match[1] + match[2] + '?data=' + digest(asset)[:16] + match[1]
        return re.sub(r'''src=(["'])(states\.js|rink-data\.js|effects\.js)(?:\?[^"']*)?\1''',
                      version, path.read_text()).encode()

    def update(self, identifier, **values):
        with self.lock:
            p = self.data / "jobs" / identifier / "job.json"
            row = json.loads(p.read_text())
            row.update(values)
            write(p, row)

    def file_url(self, path):
        from urllib.parse import quote

        relative = Path(path).resolve().relative_to(self.root)
        return "/files/" + quote(str(relative), safe="/")

    def register_video(self, path):
        import cv2

        path = self.path(path)
        if not path.is_file():
            raise ValueError("Video file does not exist")
        cap = cv2.VideoCapture(str(path))
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            if not cap.isOpened() or fps <= 0 or frames <= 0:
                raise ValueError("Cannot decode this video")
            result = {
                "id": uuid.uuid4().hex[:12],
                "path": str(path),
                "name": path.name,
                "source_sha256": digest(path),
                "fps": fps,
                "duration_s": frames / fps,
                "size_px": [
                    int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                ],
            }
        finally:
            cap.release()
        # The project holdout is reserved by the user's explicit development order.
        reservation = (
            self.root / "validation/next-match-frozen-evaluation-2026-10-26/selected-source.json"
        )
        if reservation.exists():
            saved = json.loads(reservation.read_text())
            if result["source_sha256"] == saved.get("full_source_sha256"):
                raise ValueError(
                    "This recording is reserved for the frozen evaluation; development processing is disabled."
                )
        write(self.data / "videos" / (result["id"] + ".json"), result)
        return result

    def defaults(self):
        line_path = self.path(self.profile["line_config"])
        match_path = self.path(self.profile["match_config"])
        line = json.loads(line_path.read_text())
        match = json.loads(match_path.read_text())
        return {
            "line": line["lines"][0]["endpoints_normalized"],
            "heights": match["feature_heights_m"],
            "dimensions": self.profile["state_config"],
            "teams": match["scoreboard_team_labels"],
            "profile_sha256": digest(self.profile_path),
            "rotation_status": "Experimental: handle localization tested; physical angular tracking and revolution counts unavailable.",
            "calibration_required": bool(self.profile.get("calibration_required", False)),
            "calibration": self.calibrations.options(),
        }

    def prepare(self, request):
        video = self.video(request["video_id"])
        identifier = uuid.uuid4().hex[:12]
        start = finite(request.get("start_s", 0), "start", 0)
        end = finite(request.get("end_s", video["duration_s"]), "end", 0)
        if not start < end <= video["duration_s"]:
            raise ValueError("Select an interval inside the video")
        if round(start*video['fps']) >= round(end*video['fps']):
            raise ValueError('Analysis interval must contain at least one source frame')
        requested_calibrations = request.get("calibration_ids", [])
        calibration_assets = None
        if self.profile.get("calibration_required") or requested_calibrations:
            calibration_assets = self.calibrations.selected(
                requested_calibrations, video["source_sha256"], [start, end])
            if digest(video['path']) != video['source_sha256']:
                raise ValueError('Recording changed after loading; reload and calibrate the source')
        defaults = self.defaults()
        detection_cache = None
        cache_job = request.get('detection_cache_job_id')
        if cache_job:
            from prototype.public_event_audit import verify_scan
            previous = self.data/'jobs'/self.identifier(cache_job)
            previous_spec = json.loads((previous/'spec.json').read_text())
            old_job=self.job(cache_job)
            partial=not old_job['has_completed_detector_scan']
            if partial and not old_job['committed_detector_prefix']:
                raise ValueError('Saved detector scan has no verified committed prefix')
            metadata='protocol.json' if partial else 'events.json'
            events = json.loads((previous/'observations'/metadata).read_text())
            if previous_spec['source_sha256'] != video['source_sha256'] or events['source_sha256'] != video['source_sha256']:
                raise ValueError('Saved detections must match this recording')
            if not partial and events['source_interval_s'] != [start,end]:
                raise ValueError('Saved detections must match the exact analysis interval')
            if partial and (round(events['source_interval_s'][0]*video['fps'])!=round(start*video['fps']) or
                            end<=old_job['committed_detector_prefix']['last_source_time_s']):
                raise ValueError('Resumed analysis must start on the saved grid and extend beyond its committed prefix')
            line_config = json.loads(self.path(self.profile['line_config']).read_text())
            if events['source_fps'] != video['fps']:
                raise ValueError('Saved detector scan uses a different source frame rate')
            if events['sample_step_frames'] != max(1, round(video['fps']/line_config['sample_hz'])):
                raise ValueError('Saved detector scan uses a different sampling grid')
            if partial:
                verified=old_job['committed_detector_prefix']
            else:
                with (previous/'observations/observations.jsonl').open() as stream:
                    verified = verify_scan(events, (json.loads(line) for line in stream))
            detection_cache = {'job_id': cache_job, 'path': str((previous/'observations').resolve()),
                               'scan_verification': verified,
                               'sha256': {name: digest(previous/'observations'/name) for name in
                                          ['observations.jsonl','protocol.json','config.json', 'progress.json' if partial else 'events.json']},
                               'scope': 'Detector observations only. Tracker, calibration, associations and downstream stages rerun. Exact model/runtime/decoder/adapter checks occur before replay.'}
            if partial:detection_cache['prefix_samples']=verified['verified_sampled_frames']
        raw_line = request.get("line")
        if not raw_line and calibration_assets:
            line = _calibrated_hog_line_normalized(calibration_assets) or defaults["line"]
        else:
            line = defaults["line"] if raw_line is None else raw_line
        if len(line) != 2 or any(len(p) != 2 for p in line):
            raise ValueError("Choose two event-line points")
        line = [[finite(v, "line coordinate", 0) for v in p] for p in line]
        if any(v > 1 for p in line for v in p) or line[0] == line[1]:
            raise ValueError("Invalid event line")
        teams = request.get("teams", defaults["teams"])
        if (
            len(teams) != 2
            or any(not isinstance(t, str) or not t.strip() or len(t) > 30 for t in teams)
            or teams[0] == teams[1]
        ):
            raise ValueError("Enter two distinct team names: red, then yellow")
        heights = {
            k: finite(request.get("heights", {}).get(k, v), k, 0)
            for k, v in defaults["heights"].items()
        }
        dimensions = {
            k: finite(request.get("dimensions", {}).get(k, v), k, 0.000001)
            for k, v in defaults["dimensions"].items()
            if k.endswith("_m")
        }
        if calibration_assets and abs(dimensions.get('house_radius_m', 1.829)-1.829)>1e-8:
            raise ValueError('Saved calibration uses the nominal 1.829 m outer house radius; incompatible dimensions cannot be applied')
        output = self.data / "jobs" / identifier
        output.mkdir()
        code_root = output / "code"
        code_root.mkdir()
        code_hashes = {}
        for source in (self.root / "prototype").rglob("*"):
            if not source.is_file() or source.suffix not in {
                ".py",
                ".js",
                ".html",
                ".css",
                ".yaml",
                ".yml",
            }:
                continue
            relative = source.relative_to(self.root)
            target = code_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            code_hashes[str(relative)] = digest(target)
        # Shared assets remain inputs; the observation stage hashes its actual
        # weights/references. Executable Python is frozen for every new run.
        for name in ["validation", "models", "research"]:
            if (self.root / name).exists():
                (code_root / name).symlink_to(self.root / name, target_is_directory=True)
        line_path = self.path(self.profile["line_config"])
        line_config = json.loads(line_path.read_text())
        line_config["tracker_config"] = str(
            (line_path.parent / line_config["tracker_config"]).resolve()
        )
        line_config["lines"] = [{**line_config["lines"][0], "endpoints_normalized": line}]
        match_path = self.path(self.profile["match_config"])
        match = json.loads(match_path.read_text())
        for key in ["calibration", "reference_annotations", "reference_frames", "ocr_model_dir"]:
            match[key] = str((match_path.parent / match[key]).resolve())
        if match.get('camera_foreground_checkpoint'):
            match['camera_foreground_checkpoint']=str((match_path.parent/match['camera_foreground_checkpoint']).resolve())
        match.update(feature_heights_m=heights, scoreboard_team_labels=teams)
        calibration_path = None
        if calibration_assets:
            calibration_path = self.calibrations.snapshot(calibration_assets, output, video['source_sha256'], [start, end])
            match.update(geometry_mode='explicit_source_calibration_v1',
                         source_calibration_bundle=str(calibration_path.resolve()))
        colour = json.loads(self.path(self.profile["colour_config"]).read_text())
        colour["cache_dir"] = self.profile["colour_cache"]
        state = {
            **self.profile["state_config"],
            **dimensions,
            "group_to_team": dict(zip(["red", "yellow"], teams)),
            "team_mapping_provenance": "User-supplied team/handle-colour metadata",
        }
        for name, value in [
            ("line.json", line_config),
            ("match.json", match),
            ("colour.json", colour),
            ("state.json", state),
        ]:
            write(output / name, value)
        spec = {
            "schema_version": "curling-product-job-v1",
            "video": video["path"],
            "source_sha256": video["source_sha256"],
            "video_url": "/media/" + video["id"],
            "video_id": video["id"],
            "output": str(output),
            "start_s": start,
            "end_s": end,
            "line_config": str(output / "line.json"),
            "match_config": str(output / "match.json"),
            "state_config": str(output / "state.json"),
            "colour_config": str(output / "colour.json"),
            "profile": self.profile,
            "profile_sha256": digest(self.profile_path),
            "code_root": str(code_root),
            "code_sha256": code_hashes,
            "evaluation_scope": "Development run; not independent transfer validation.",
            "calibration_ids": requested_calibrations,
            "calibration_bundle_sha256": digest(calibration_path) if calibration_path else None,
            "detection_cache": detection_cache,
        }
        write(output / "spec.json", spec)
        write(
            output / "job.json",
            {
                "id": identifier,
                "name": request.get("name") or video["name"],
                "created_at": time.time(),
                "state": "queued",
                "message": "Queued",
                "stage": None,
                "stages": [],
                "video_id": video["id"],
                "source_sha256": video["source_sha256"],
                "start_s": start,
                "end_s": end,
                "result_url": None,
                "rotation_status": defaults["rotation_status"],
                "imported": False,
                "calibration_origin": "explicit_operator_markings" if calibration_assets else "legacy_experimental_geometry",
                "detection_cache_job_id": cache_job,
            },
        )
        return identifier

    def submit(self, request):
        identifier = self.prepare(request)
        self.schedule(identifier)
        return self.job(identifier)

    def schedule(self,identifier):
        future=self.pool.submit(self.execute,identifier)
        def finished(result):
            if result.cancelled():return
            error=result.exception()
            if error is None:return
            import traceback
            traceback.print_exception(error)
            failure={'state':'failed','stage':None,'message':f'Worker failed: {type(error).__name__}: {error}'}
            with self.lock:
                self.runtime_failures[identifier]=failure
                try:
                    self.update(identifier,**failure)
                    self.runtime_failures.pop(identifier,None)
                except OSError:pass
        future.add_done_callback(finished)
        return future

    def retry(self, identifier):
        """Reprocess a verified completed scan, preserving the failed run intact."""
        return self._rebuild_outputs(identifier,allow_completed=False)

    def rebuild_outputs(self,identifier):
        """Use current downstream code on frozen observations in a new job."""
        return self._rebuild_outputs(identifier,allow_completed=True)

    def _rebuild_outputs(self,identifier,*,allow_completed):
        from prototype.public_event_audit import verify_scan

        previous = self.data / "jobs" / self.identifier(identifier)
        old = json.loads((previous / "spec.json").read_text())
        allowed=['failed','interrupted','cancelled']+(['done'] if allow_completed else [])
        if self.job(identifier)["state"] not in allowed:
            raise ValueError("Only an unfinished run can be retried")
        events = json.loads((previous / "observations/events.json").read_text())

        def rows(name):
            with (previous / "observations" / name).open() as stream:
                for line in stream:
                    yield json.loads(line)

        scan = verify_scan(events, rows("observations.jsonl"))
        verify_scan(events, rows("match-observations.jsonl"))
        if events["source_sha256"] != old["source_sha256"]:
            raise ValueError("Saved observations do not match the source")
        match = json.loads((previous / "match.json").read_text())
        line = json.loads((previous / "line.json").read_text())
        state = json.loads((previous / "state.json").read_text())
        new = self.prepare(
            {
                "video_id": old["video_id"],
                "start_s": old["start_s"],
                "end_s": old["end_s"],
                "name": self.job(identifier)["name"] + (" · rebuilt outputs" if allow_completed else " · retry"),
                "teams": match["scoreboard_team_labels"],
                "line": line["lines"][0]["endpoints_normalized"],
                "heights": match["feature_heights_m"],
                "dimensions": state,
                "calibration_ids": old.get("calibration_ids", []),
            }
        )
        output = self.data / "jobs" / new
        try:
            for name in ["line.json", "match.json", "state.json", "colour.json"]:
                shutil.copyfile(previous / name, output / name)
            shutil.copytree(previous / "observations", output / "observations",symlinks=True)
            spec = json.loads((output / "spec.json").read_text())
            spec["reused_observations_from"] = identifier
            spec['observation_reuse_scope']='Frozen detections, tracking and geometry copied with input hashes; current downstream code reruns in a separate development job. Original outputs remain unchanged.'
            spec["reused_scan_verification"] = scan
            spec["reused_input_sha256"] = {
                name: digest(previous / "observations" / name)
                for name in [
                    "events.json",
                    "observations.jsonl",
                    "match-observations.jsonl",
                    "score-observations.jsonl",
                ]
            }
            write(output / "spec.json", spec)
            self.update(
                new,
                reused_observations_from=identifier,
                message="Verified completed observations reused; rebuilding remaining outputs",
            )
            self.schedule(new)
        except Exception as exc:
            self.update(new, state="failed", message=str(exc))
            raise
        return self.job(new)

    def execute(self, identifier):
        if identifier in self.cancelled:
            self.update(identifier, state="cancelled", message="Cancelled before processing")
            return
        output = self.data / "jobs" / identifier
        spec = json.loads((output / "spec.json").read_text())
        if digest(spec["video"]) != spec["source_sha256"]:
            self.update(
                identifier,
                state="failed",
                message="Source video changed since loading; load the recording again.",
            )
            return
        p = spec["profile"]
        code_root = Path(spec["code_root"])
        # Preserve the venv executable path: resolving its symlink loses the venv.
        inference = (self.root / p["inference_python"]).absolute()
        state_python = (self.root / p["state_python"]).absolute()
        required = [inference, state_python, self.path(p["detector_checkpoint"])]
        if p["detector_backend"] == "openvino_gpu":
            required.append(self.path(p["detector_export"]))
        for path in required:
            if not path.exists():
                self.update(
                    identifier, state="failed", message="Missing runtime dependency: " + str(path)
                )
                return
        env = {
            **os.environ,
            **p.get("runtime_environment", {}),
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
        }
        wrapper = str(self.root / "feasibility/scripts/python.sh")
        spec_path = str(output / "spec.json")
        observation = [
            wrapper,
            "prototype/scripts/run_throw_pipeline.py",
            "--video",
            spec["video"],
            "--source-id",
            identifier,
            "--start",
            str(spec["start_s"]),
            "--end",
            str(spec["end_s"]),
            "--event-line-config",
            spec["line_config"],
            "--events-only",
            "--match-state-config",
            spec["match_config"],
            "--stone-detector-checkpoint",
            str(self.path(p["detector_checkpoint"])),
            "--stone-detector-backend",
            p["detector_backend"],
            "--output-dir",
            str(output / "observations"),
        ]
        if p["detector_backend"] == "openvino_gpu":
            observation += ["--stone-detector-export", str(self.path(p["detector_export"]))]
        if spec.get('detection_cache'):
            cache = spec['detection_cache']
            for name, expected in cache['sha256'].items():
                if digest(Path(cache['path'])/name) != expected:
                    self.update(identifier, state='failed', message='Saved detector scan changed after analysis was queued')
                    return
            observation += ['--detection-cache', cache['path']]
            if cache.get('prefix_samples'):
                observation += ['--detection-cache-prefix-samples',str(cache['prefix_samples'])]
        stages = [
            ("observations", inference, [], observation),
            (
                "colour",
                inference,
                [p["colour_dependencies"]],
                [
                    wrapper,
                    "-m",
                    "prototype.scripts.classify_event_colours",
                    "--video",
                    spec["video"],
                    "--events",
                    str(output / "observations/events.json"),
                    "--output",
                    str(output / "event-colours.json"),
                    "--config",
                    spec["colour_config"],
                ],
            ),
            (
                "stone_colours",
                inference,
                [p["colour_dependencies"]],
                [
                    wrapper,
                    "-m",
                    "prototype.track_colours",
                    "--public-run",
                    str(output / "observations"),
                    "--video",
                    spec["video"],
                    "--output",
                    str(output / "track-colours.json"),
                    "--config",
                    spec["colour_config"],
                ],
            ),
            (
                "trajectories",
                inference,
                [],
                [
                    wrapper,
                    "-m",
                    "prototype.product_pipeline",
                    "--stage",
                    "assemble",
                    "--spec",
                    spec_path,
                ],
            ),
            (
                "boards",
                state_python,
                [p["state_dependencies"]],
                [
                    wrapper,
                    "-m",
                    "prototype.product_pipeline",
                    "--stage",
                    "boards",
                    "--spec",
                    spec_path,
                ],
            ),
            (
                "report",
                state_python,
                [],
                [
                    wrapper,
                    "-m",
                    "prototype.product_pipeline",
                    "--stage",
                    "finish",
                    "--spec",
                    spec_path,
                ],
            ),
        ]
        if spec.get("reused_observations_from"):
            stages[0] = (
                "observation_view",
                inference,
                [],
                [
                    wrapper,
                    "-m",
                    "prototype.product_pipeline",
                    "--stage",
                    "observation-view",
                    "--spec",
                    spec_path,
                ],
            )
        started = time.time()
        record = []
        try:
            for name, python, extra, command in stages:
                if identifier in self.cancelled:
                    raise InterruptedError("Cancelled")
                self.update(
                    identifier,
                    state="running",
                    stage=name,
                    message={
                        "observations": "Detecting and tracking stones",
                        "observation_view": "Reusing verified observations and rebuilding views",
                        "colour": "Classifying stone colours",
                        "trajectories": "Building trajectory views",
                        "stone_colours": "Classifying colours of all tracked stones",
                        "boards": "Building synchronized board state",
                        "report": "Preparing report",
                    }[name],
                    started_at=started,
                    stages=record,
                )
                stage_start = time.time()
                stage = {
                    "stage": name,
                    "command": command,
                    "started_at": stage_start,
                    "state": "running",
                }
                record.append(stage)
                write(output / "stages.json", record)
                stage_env = {
                    **env,
                    "CURLING_PYTHON": str(python),
                    "PYTHONPATH": os.pathsep.join(
                        [str(code_root), str(code_root / "prototype"), *extra]
                    ),
                }
                if name in ("colour", "stone_colours"):
                    stage_env["HF_HUB_OFFLINE"] = "1"
                with (output / (name + ".log")).open("w") as log:
                    process = subprocess.Popen(
                        command, cwd=code_root, env=stage_env, stdout=log, stderr=subprocess.STDOUT
                    )
                    with self.lock:
                        self.processes[identifier] = process
                    code = process.wait()
                    with self.lock:
                        self.processes.pop(identifier, None)
                stage.update(
                    state="done" if code == 0 else "failed",
                    exit_code=code,
                    wall_s=time.time() - stage_start,
                )
                write(output / "stages.json", record)
                if identifier in self.cancelled:
                    raise InterruptedError("Cancelled")
                if code:
                    raise RuntimeError(name + " failed; see " + name + ".log")
            summary = json.loads((output / "result/summary.json").read_text())
            self.update(
                identifier,
                state="done",
                stage=None,
                message=("Processing finished: calibration gaps; metric trajectories are incomplete"
                         if summary.get('calibration', {}).get('status') == 'gaps_present'
                         else "Processing finished: camera associations need review"
                         if summary.get('trajectory_status') == 'incomplete'
                         else "Processing finished; accuracy and identity require review"),
                stages=record,
                wall_s=time.time() - started,
                result_url=self.file_url(output / "result/index.html"),
                board_url=self.file_url(output / "result/boards/index.html"),
                trajectory_url=self.file_url(output / "result/trajectories/index.html"),
                summary=summary,
                calibration_url=(self.file_url(output/'result/calibration/index.html') if (output/'result/calibration/index.html').exists() else None),
            )
        except Exception as exc:
            self.update(
                identifier,
                state="cancelled" if isinstance(exc, InterruptedError) else "failed",
                message=str(exc),
                stages=record,
                wall_s=time.time() - started,
            )

    def cancel(self, identifier):
        self.identifier(identifier)
        if self.job(identifier)["externally_managed"]:
            raise ValueError("This run is managed by another worker")
        self.cancelled.add(identifier)
        if self.job(identifier)["state"] == "queued":
            self.update(identifier, state="cancelled", message="Cancelled before processing")
        with self.lock:
            process = self.processes.get(identifier)
            if process:
                process.terminate()
        return {"status": "cancellation_requested"}

    def import_result(self, viewer, video, trajectory=None, name=None):
        viewer = self.path(viewer)
        self.file_url(viewer / "index.html")
        manifest = json.loads((viewer / "manifest.json").read_text())
        asset = self.register_video(video)
        if manifest["source_sha256"] != asset["source_sha256"]:
            raise ValueError("Result belongs to a different video")
        states = json.loads((viewer / "states.json").read_text())
        trajectory_url = self.file_url(trajectory) if trajectory else None
        evidence = {
            "board_states_sha256": digest(viewer / "states.json"),
            "source_sha256": asset["source_sha256"],
        }
        if trajectory:
            data_path = self.path(trajectory).parent / "rink-data.js"
            text = data_path.read_text()
            assignment = re.fullmatch(r"\s*window\.RINK_DATA\s*=\s*(.*);\s*", text, flags=re.DOTALL)
            if not assignment:
                raise ValueError("Expected a shared-rink trajectory viewer")
            data = json.loads(assignment[1])
            if (data.get("provenance") or {}).get("source_sha256") != asset["source_sha256"]:
                raise ValueError("Trajectory viewer belongs to a different video")
            board_events = {e["event_id"]: e["crossing_time_s"] for e in states["events"]}
            trajectory_events = {e["id"]: e["time_s"] for e in data["events"]}
            if board_events != trajectory_events:
                raise ValueError("Trajectory and board candidate IDs/timestamps do not match")
            evidence.update(trajectory_data_sha256=digest(data_path), candidate_id_times_match=True)
        for existing in self.jobs():
            if (
                existing.get("imported")
                and existing.get("board_url") == self.file_url(viewer / "index.html")
                and existing["source_sha256"] == asset["source_sha256"]
            ):
                if trajectory_url and existing.get("trajectory_url") not in [None, trajectory_url]:
                    continue
                self.update(
                    existing["id"],
                    trajectory_url=trajectory_url or existing.get("trajectory_url"),
                    import_evidence={**existing.get("import_evidence", {}), **evidence},
                )
                return self.job(existing["id"])
        identifier = uuid.uuid4().hex[:12]
        out = self.data / "jobs" / identifier
        out.mkdir()
        result = {
            "id": identifier,
            "name": name or asset["name"],
            "created_at": time.time(),
            "state": "done",
            "stage": None,
            "message": "Imported existing development output; no inference rerun",
            "imported": True,
            "stages": [],
            "video_id": asset["id"],
            "source_sha256": asset["source_sha256"],
            "result_url": self.file_url(viewer / "index.html"),
            "board_url": self.file_url(viewer / "index.html"),
            "trajectory_url": trajectory_url,
            "import_evidence": evidence,
            "events_path": str(viewer / "states.json"),
            "summary": {
                **states["summary"],
                "observed_board_frames": len(states.get("timeline", {}).get("times", [])),
                "measurement_scope": "Availability, not independent accuracy.",
                "physical_revolutions": None,
            },
            "rotation_status": self.defaults()["rotation_status"],
        }
        write(out / "job.json", result)
        return result

    def events(self, identifier):
        row = self.job(identifier)
        path = (
            Path(row["events_path"])
            if row.get("events_path")
            else self.data / "jobs" / identifier / "result/boards/states.json"
        )
        if not path.exists():
            return []
        doc = json.loads(path.read_text())
        effects_path = self.data / "jobs" / identifier / "result/throws/effects.json"
        clips = {}
        if effects_path.is_file():
            for effect in json.loads(effects_path.read_text())["events"]:
                quiet = effect.get("settle_interval_s")
                if quiet and effect.get("arrival_time_s") is not None:
                    # Include the departure crossing, the receiving approach, and both quiet-window bounds.
                    start = min(effect["crossing_time_s"], effect["arrival_time_s"]) - 2
                    clips[effect["event_id"]] = [max(row.get("start_s") or 0, start), *quiet]
        scores = {entry['event_id']: entry
                  for entry in doc.get('detected_throw_scoring', {}).get('history', [])}
        return [
            {
                "event_id": e["event_id"],
                "time_s": e["crossing_time_s"],
                "review_clip_s": clips.get(e["event_id"]),
                "proposal_time_s": e["proposal"].get("time_s"),
                "post_throw_points": scores.get(e['event_id'], {}).get('estimated_points'),
                "post_throw_point_status": scores.get(e['event_id'], {}).get('status', 'unavailable'),
                "status": e["proposal"]["status"],
                "physical_revolutions": e.get("physical_revolutions"),
            }
            for e in doc["events"]
        ]

    def stone_histories(self, identifier):
        from prototype.stone_history import from_job
        job = self.data/'jobs'/self.identifier(identifier)
        if json.loads((job/'job.json').read_text())['state'] != 'done':
            raise ValueError('Stone history requires a completed run')
        with self.history_lock:
            if identifier not in self.history_cache:
                data = from_job(job)
                if len(self.history_cache) >= 8:
                    self.history_cache.pop(next(iter(self.history_cache)))
                self.history_cache[identifier] = data
            return self.history_cache[identifier]

    def reviews(self, identifier):
        path = self.data / "jobs" / self.identifier(identifier) / "reviews.json"
        return json.loads(path.read_text()) if path.exists() else {}

    def review(self, identifier, request):
        if request["event_id"] not in {e["event_id"] for e in self.events(identifier)}:
            raise ValueError("Unknown candidate")
        if request["label"] not in ["throw", "false_detection", "uncertain"]:
            raise ValueError("Choose a review label")
        with self.lock:
            rows = self.reviews(identifier)
            rows[request["event_id"]] = {
                "label": request["label"],
                "note": str(request.get("note", "")),
                "reviewer": str(request.get("reviewer", "user")),
                "prediction_visible": True,
                "independent_ground_truth": False,
                "reviewed_at": time.time(),
            }
            write(self.data / "jobs" / identifier / "reviews.json", rows)
        return rows

    def score_and_rocks(self, identifier):
        folder = self.data / "jobs" / self.identifier(identifier)
        saved = folder / "result/score-and-rocks.json"
        if saved.exists():
            return json.loads(saved.read_text())
        agg = folder / "result/aggregate-rink.json"
        eff = folder / "result/throws/effects.json"
        state_cfg = folder / "state.json"
        if not (agg.exists() and eff.exists() and state_cfg.exists()):
            return {"ends": [], "throws": [], "rock_pair_summary": [], "summary": {}}
        from prototype.match_score_and_rocks import build as build_score_and_rocks
        rev = folder / "result/throws/revolutions.json"
        score_obs = folder / "observations/score-observations.jsonl"
        return build_score_and_rocks(
            aggregate=agg,
            effects=eff,
            state_config=state_cfg,
            score_observations=score_obs if score_obs.exists() else None,
            revolutions=rev if rev.exists() else None,
        )

    def report(self, identifier):
        job = self.job(identifier)
        reviews = job.pop("reviews")
        tp = sum(r["label"] == "throw" for r in reviews.values())
        fp = sum(r["label"] == "false_detection" for r in reviews.values())
        folder = self.data / "jobs" / identifier
        evidence = {}
        for key, path in {
            "specification": folder / "spec.json",
            "observation_protocol": folder / "observations/protocol.json",
            "source_calibration": folder / "camera-calibration.json",
            "geometry_coverage": folder / "observations/match-observation-summary.json",
        }.items():
            if path.exists():
                evidence[key] = json.loads(path.read_text())
        if job.get("events_path"):
            manifest = Path(job["events_path"]).parent / "manifest.json"
            if manifest.exists():
                evidence["imported_result_manifest"] = json.loads(manifest.read_text())
        states_path = (Path(job["events_path"]) if job.get("events_path")
                       else folder / "result/boards/states.json")
        score_tracking = None
        detected_throw_scoring = None
        if states_path.exists():
            state_payload = json.loads(states_path.read_text())
            score_tracking = state_payload.get("score_tracking")
            detected_throw_scoring = state_payload.get("detected_throw_scoring")
            if score_tracking is not None:
                score_tracking = {key: value for key, value in score_tracking.items()
                                  if key != "timeline"}
        return {
            "job": job,
            "pipeline_evidence": evidence,
            "score_tracking": score_tracking,
            "detected_throw_scoring": detected_throw_scoring,
            "candidate_reviews": reviews,
            "review_summary": {
                "reviewed_throws": tp,
                "reviewed_false_detections": fp,
                "uncertain": sum(r["label"] == "uncertain" for r in reviews.values()),
                "precision_on_reviewed_decidable_candidates": tp / (tp + fp) if tp + fp else None,
                "recall": None,
                "scope": "User reviews with predictions visible; subset precision only. Missed throws have not been exhaustively labelled.",
            },
            "physical_revolutions": None,
            "rotation_status": job["rotation_status"],
        }


class Handler(VideoHandler):
    def __init__(self, *args, app, **kwargs):
        self.app = app
        SimpleHTTPRequestHandler.__init__(self, *args, directory=str(app.root), **kwargs)

    def translate_path(self, path):
        path = unquote(urlsplit(path).path)
        if path.startswith("/media/"):
            try:
                return self.app.video(path.split("/")[2])["path"]
            except (ValueError, FileNotFoundError):
                return str(self.app.data / "missing")
        if path.startswith("/files/"):
            candidate = (self.app.root / path.removeprefix("/files/")).resolve()
            if candidate.is_relative_to(self.app.root):
                return str(candidate)
        return str(self.app.data / "missing")

    def end_headers(self):
        path = urlsplit(self.path).path
        if path == "/" or path.startswith("/api/") or path in ("/files/prototype/calibration_ui.js","/files/prototype/calibration_template.js"):
            self.send_header("Cache-Control", "no-store")
        elif path.endswith((".html", "/states.js", "/rink-data.js")):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
        path = urlsplit(self.path).path
        try:
            if path == "/":
                content = WEB.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            if path == "/api/defaults":
                return self.respond(200, self.app.defaults())
            if path == "/api/jobs":
                return self.respond(200, self.app.jobs())
            if path == "/api/calibrations":
                video_id = parse_qs(urlsplit(self.path).query).get('video_id', [''])[0]
                return self.respond(200, self.app.calibrations.list(video_id))
            match = re.fullmatch(r"/api/jobs/([a-f0-9]{12})(?:/(events|report|logs|stone-histories|score-and-rocks))?", path)
            if match:
                identifier, action = match.groups()
                if action == "stone-histories":
                    return self.respond(200, self.app.stone_histories(identifier))
                if action == "score-and-rocks":
                    return self.respond(200, self.app.score_and_rocks(identifier))
                if action == "events":
                    return self.respond(200, self.app.events(identifier))
                if action == "report":
                    return self.respond(200, self.app.report(identifier))
                if action == "logs":
                    logs = {
                        p.stem: p.read_text(errors="replace")[-20000:]
                        for p in (self.app.data / "jobs" / identifier).glob("*.log")
                    }
                    return self.respond(200, logs)
                return self.respond(200, self.app.job(identifier))
            if path.startswith(("/files/", "/media/")):
                target = Path(self.translate_path(self.path))
                if path.startswith("/files/") and target.suffix == ".html" and target.is_file():
                    content = self.app.viewer_html(target)
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(content)))
                    self.end_headers()
                    self.wfile.write(content)
                    return
                return SimpleHTTPRequestHandler.do_GET(self)
            return self.respond(404, {"error": "Unknown endpoint"})
        except (ValueError, KeyError, FileNotFoundError) as exc:
            return self.respond(400, {"error": str(exc)})

    def do_POST(self):
        parsed = urlsplit(self.path)
        path = parsed.path
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if path == "/api/upload":
                if not 0 < size <= self.app.profile["max_upload_bytes"]:
                    raise ValueError("Empty video or upload exceeds configured limit")
                name = Path(parse_qs(parsed.query).get("name", ["video.mp4"])[0]).name
                name = re.sub(r"[^A-Za-z0-9._-]", "_", name)[:120]
                target = self.app.data / "uploads" / (uuid.uuid4().hex + "-" + name)
                remaining = size
                with target.open("wb") as stream:
                    while remaining:
                        chunk = self.rfile.read(min(1024 * 1024, remaining))
                        if not chunk:
                            raise ValueError("Incomplete upload")
                        stream.write(chunk)
                        remaining -= len(chunk)
                return self.respond(201, self.app.register_video(target))
            if not 0 < size <= 1024 * 1024:
                raise ValueError("Invalid request size")
            request = json.loads(self.rfile.read(size))
            if path == "/api/videos":
                return self.respond(201, self.app.register_video(request["path"]))
            if path == "/api/calibrations/frames":
                return self.respond(201, self.app.calibrations.frame(request))
            if path == "/api/calibrations/preview":
                return self.respond(200, self.app.calibrations.preview(request))
            if path == "/api/calibrations/template-hog-edit":
                from prototype.rink_template import edit_hog_handle
                return self.respond(200,edit_hog_handle(request['parameters'],request['panel'],
                    request['target_native_px'],request['maximum_house_drift_px'],request.get('house_parameters')))
            if path == "/api/calibrations":
                return self.respond(201, self.app.calibrations.confirm(request))
            if path == "/api/jobs":
                return self.respond(202, self.app.submit(request))
            if path == "/api/import":
                return self.respond(
                    201,
                    self.app.import_result(
                        request["viewer"],
                        request["video"],
                        request.get("trajectory"),
                        request.get("name"),
                    ),
                )
            match = re.fullmatch(r"/api/jobs/([a-f0-9]{12})/(review|cancel|retry|rebuild)", path)
            if match:
                identifier, action = match.groups()
                if action == "retry":
                    return self.respond(202, self.app.retry(identifier))
                if action=='rebuild':
                    return self.respond(202,self.app.rebuild_outputs(identifier))
                return self.respond(
                    200,
                    self.app.review(identifier, request)
                    if action == "review"
                    else self.app.cancel(identifier),
                )
            return self.respond(404, {"error": "Unknown endpoint"})
        except (ValueError, KeyError, FileNotFoundError, TypeError) as exc:
            return self.respond(400, {"error": str(exc)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-job", action="append", default=[], help="Active job managed by a separate worker; preserve it during startup recovery")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--data", type=Path)
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--import-result", type=Path)
    parser.add_argument("--video", type=Path)
    parser.add_argument("--trajectory", type=Path)
    args = parser.parse_args()
    try:
        with own_data_directory(args.data or ROOT/'workbench-data'):
            # Bind before startup recovery: a second server on an occupied port
            # must not mark existing jobs interrupted as a side effect.
            with ThreadingHTTPServer(("127.0.0.1", args.port), Handler) as server:
                app = Workbench(data=args.data, profile=args.profile, external_jobs=args.external_job)
                server.RequestHandlerClass=partial(Handler,app=app)
                if args.import_result:
                    if not args.video:parser.error("--import-result requires --video")
                    app.import_result(args.import_result,args.video,args.trajectory)
                print(f"Curling workbench: http://127.0.0.1:{server.server_port}",flush=True)
                try:server.serve_forever()
                except KeyboardInterrupt:pass
                finally:app.pool.shutdown(wait=False,cancel_futures=True)
    except ValueError as exc:parser.error(str(exc))


if __name__ == "__main__":
    main()
