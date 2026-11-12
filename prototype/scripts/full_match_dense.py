"""Memory-safe, resumable dense CoTracker stage for every event in an aggregate.

The frozen pipeline's monolithic dense run keeps every event's pixel tracks in
memory and embeds all of them in one HTML report. For a full match that is
~19 h of tracking followed by a multi-gigabyte report that can exhaust memory.
This orchestrator performs the same per-segment work with the same frozen spin
implementation, but:

  * processes every event (no candidate subset),
  * reuses a completed per-segment result on resume,
  * writes a per-event two-view viewer and keeps only summary metadata in memory,
  * writes a lightweight global index.

It does not change tracking, seeds, calibration or identity rules. Physical
identity remains unverified.
"""

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

DEV_ROOT = Path("/home/user/curling-baseline-recovery-development")
if str(DEV_ROOT) not in sys.path:
    sys.path.insert(0, str(DEV_ROOT))

from prototype.spin.identity import continuity_annotations  # noqa: E402
from prototype.spin.pipeline import candidate_config, run  # noqa: E402
from prototype.spin.point_tracking import digest  # noqa: E402
from prototype.spin.projection import feature_heights  # noqa: E402
from prototype.spin.throw_report import write_report  # noqa: E402
from prototype.spin.throws import (  # noqa: E402
    association,
    event_source_time,
    handoff_observations,
    visibility_intervals,
)

DEPARTURE_EVENT_WINDOW_S = 15.0
RECEIVING_EVENT_BUDGET_S = 40.0


def episode_interval(event, segment, *, source_end_s, fps):
    """Clip a tracker lifetime to the throw episode it represents.

    Primary segments can follow a tracker ID for hundreds of seconds. Dense
    tracking must cover the delivery/receiving episode, not the ID lifetime.
    The start is an existing observation so the frozen automatic seeding rule
    remains valid. This is an episode policy, not a candidate subset.
    """
    points = sorted(segment.get("pixel_points") or [], key=lambda p: p["time_s"])
    if not points:
        return None
    role = segment.get("role")
    evidence = segment.get("role_evidence") or {}
    hog = segment.get("hog_crossing_evidence") or {}
    prediction = event.get("event_prediction") or {}
    centre = None
    interval = evidence.get("interval_s")
    if interval and len(interval) == 2:
        centre = sum(interval) / 2.0
    if centre is None and hog.get("crossing_time_s") is not None:
        centre = float(hog["crossing_time_s"])
    if centre is None and prediction.get("crossing_time_s") is not None:
        centre = float(prediction["crossing_time_s"])
    if centre is None:
        centre = points[0]["time_s"]
    if role == "departure":
        target = centre - 3.0
        chosen = min(points, key=lambda p: abs(p["time_s"] - target))
        start = chosen["time_s"]
        end = min(points[-1]["time_s"] + 1.0 / fps,
                  start + DEPARTURE_EVENT_WINDOW_S, source_end_s)
        policy = {"end_reason": "departure_event_window",
                  "budget_s": DEPARTURE_EVENT_WINDOW_S,
                  "centre_s": centre, "start_s": start, "end_s": end,
                  "legacy_track_span_s": points[-1]["time_s"] - points[0]["time_s"],
                  "physical_identity_verified": False}
    elif role == "receiving":
        target = centre - 2.0
        chosen = min(points, key=lambda p: abs(p["time_s"] - target))
        start = chosen["time_s"]
        end = min(points[-1]["time_s"] + 1.0 / fps,
                  start + RECEIVING_EVENT_BUDGET_S, source_end_s)
        policy = {"end_reason": "receiving_event_budget",
                  "budget_s": RECEIVING_EVENT_BUDGET_S,
                  "centre_s": centre, "start_s": start, "end_s": end,
                  "legacy_track_span_s": points[-1]["time_s"] - points[0]["time_s"],
                  "physical_stop_detected": False,
                  "physical_identity_verified": False}
    else:
        return None
    if end <= start:
        return None
    return [start, end], policy


def summary_row(event, row):
    """Keep only metadata; tracks stay in per-segment result files."""
    keep = ("segment_id", "camera", "role", "status", "reason", "report",
            "result", "result_sha256", "visibility_intervals",
            "identity_continuity", "projection", "model", "fps",
            "point_names", "episode_policy", "scene_initialization")
    return {
        "candidate_id": row["candidate_id"],
        "event_time_s": row["event_time_s"],
        "association": row["association"],
        "baseline_failure_reasons": row["baseline_failure_reasons"],
        "handoffs": row["handoffs"],
        "missing_roles": row["missing_roles"],
        "segments": [{k: segment.get(k) for k in keep}
                     for segment in row["segments"]],
    }


def global_row(row):
    """Lean row for the run-level result; per-event summary keeps projection detail."""
    return {
        "candidate_id": row["candidate_id"],
        "event_time_s": row["event_time_s"],
        "association": row["association"],
        "baseline_failure_reasons": row["baseline_failure_reasons"],
        "handoffs": row["handoffs"],
        "missing_roles": row["missing_roles"],
        "segments": [{
            "segment_id": s.get("segment_id"),
            "camera": s.get("camera"),
            "role": s.get("role"),
            "status": s.get("status"),
            "reason": s.get("reason"),
            "visibility_intervals": s.get("visibility_intervals"),
            "result_sha256": s.get("result_sha256"),
            "reused": s.get("reused"),
        } for s in row["segments"]],
    }


def run_event(video, aggregate_path, output, event_index, event, *, checkpoint,
              mode, device, threads, expected_decoder_sha, stone_detector,
              heights, tracking_progress_dir, source_end_s, fps):
    event_dir = output / f"event-{event_index:04d}"
    event_dir.mkdir(parents=True, exist_ok=True)
    row = {"candidate_id": event["candidate_id"],
           "association": association(event),
           "event_time_s": event_source_time(event),
           "baseline_failure_reasons": event.get("failure_reasons", []),
           "segments": []}
    results = {}
    for segment_index, segment in enumerate(event["segments"]):
        sid = segment["segment_id"]
        folder = event_dir / f"segment-{segment_index:02d}"
        entry = {"segment_id": sid, "camera": segment["camera"],
                 "role": segment.get("role"), "status": "pending",
                 "report": None}
        row["segments"].append(entry)
        if (segment["camera"] not in ("left_split", "right_split")
                or not segment.get("pixel_points")):
            entry.update(status="unavailable",
                         reason="No nonempty split-camera observations")
            continue
        result_path = folder / "result.json"
        if result_path.exists():
            try:
                result = json.loads(result_path.read_text())
                entry.update(status="tracked", reused=True)
            except json.JSONDecodeError:
                result = None
            if result is not None:
                results[sid] = result
                _fill_entry(entry, folder, result, segment, event)
                continue
        if folder.exists():
            failed = folder.with_name(
                folder.name + f".failed-{int(time.time())}")
            folder.rename(failed)
        config_path = event_dir / f"config-{segment_index:02d}.json"
        try:
            config = candidate_config(video, aggregate_path, sid,
                                      receiving_scene=True)
            clipped = episode_interval(event, segment,
                                       source_end_s=source_end_s, fps=fps)
            if clipped is not None:
                config["interval_s"], config["episode_policy"] = clipped
                if segment["camera"] != "right_split":
                    config["receiving_scene"] = False
            if tracking_progress_dir is not None:
                config["tracking_progress_directory"] = str(
                    Path(tracking_progress_dir).resolve())
            if heights is not None:
                config["feature_heights_m"] = heights
            if stone_detector is not None:
                config["stone_detector"] = stone_detector.provenance
            config_path.write_text(json.dumps(config, indent=2) + "\n")
            result = run(video, config_path, folder, checkpoint=checkpoint,
                         device=device, mode=mode, threads=threads,
                         aggregate_path=aggregate_path,
                         expected_decoder_sha=expected_decoder_sha,
                         stone_detector=stone_detector)
            results[sid] = result
            entry.update(status="tracked", reused=False)
            _fill_entry(entry, folder, result, segment, event)
        except (ValueError, RuntimeError, OSError) as exc:
            entry.update(status="failed",
                         reason=f"{type(exc).__name__}: {exc}")
    row["handoffs"] = handoff_observations(row["association"], results)
    row["missing_roles"] = [
        role for role in ("departure", "receiving")
        if not any(segment["role"] == role and segment["status"] == "tracked"
                   for segment in row["segments"])]
    # Per-event two-view viewer; embeds only this event's tracks.
    report = {
        "schema_version": "two-view-dense-development-v1",
        "events": [row],
        "scope": "Per-event dense tracking; physical identity and geometry unvalidated.",
        "source_sha256": digest(video),
        "aggregate_sha256": digest(aggregate_path),
        "source_interval_s": None,
        "checkpoint_sha256": digest(checkpoint),
        "physical_identity_verified": False,
        "selection": event["candidate_id"],
        "code_sha256": {},
        "match_observation_run": event.get("provenance_run"),
    }
    aggregate = json.loads(Path(aggregate_path).read_text())
    report["source_interval_s"] = aggregate.get("source_interval_s")
    report["match_observation_run"] = (
        aggregate.get("provenance") or {}).get("match_observation_run")
    try:
        write_report(report, event_dir, video, stone_detector=stone_detector)
    except (ValueError, OSError) as exc:
        (event_dir / "viewer-failure.json").write_text(
            json.dumps({"error": f"{type(exc).__name__}: {exc}"}, indent=2) + "\n")
    result_row = summary_row(event, row)
    (event_dir / "summary.json").write_text(
        json.dumps(result_row, indent=2, allow_nan=False) + "\n")
    return result_row


def _fill_entry(entry, folder, result, segment, event):
    entry.update(
        status="tracked",
        report=f"{folder.name}/index.html",
        result=f"{folder.name}/result.json",
        result_sha256=digest(folder / "result.json"),
        visibility_intervals=visibility_intervals(result),
        identity_continuity=continuity_annotations(
            result["times_s"], result["point_visible"], result["point_names"]),
        projection=result.get("projection"),
        model=result.get("model"),
        fps=result.get("fps"),
        point_names=result.get("point_names"),
        times_s=result.get("times_s"),
        tracks_px=result.get("tracks_px"),
        point_visible=result.get("point_visible"),
        episode_policy=result.get("config", {}).get("episode_policy"),
        scene_initialization=result.get("config", {}).get("scene_initialization"),
    )


INDEX = """<!doctype html><meta charset="utf-8"><title>Dense two-view tracks — all events</title>
<style>body{font:16px system-ui;max-width:1100px;margin:24px;color:#20323d}h1{font-size:24px}table{border-collapse:collapse;width:100%}td,th{padding:7px;border-bottom:1px solid #dce5e8;text-align:left}code{font-size:13px}.note{border-left:4px solid #c88700;background:#fff5df;padding:10px}</style>
<h1>Dense two-view tracks — every event</h1>
<p class="note">Development. One page per event; each page embeds only that event's dense tracks and opens the source video at its interval. Physical identity is unverified; query IDs are not physical stone identities. The shared-rink viewer is separate.</p>
<p>__SUMMARY__</p>
<table><tr><th>#</th><th>Event</th><th>Time (s)</th><th>Association</th><th>Segments tracked</th><th>Viewer</th></tr>__ROWS__</table>
<p><a href="../index.html">Back to run index</a></p>
"""


def write_index(output, rows):
    body = []
    for index, row in enumerate(rows):
        tracked = sum(1 for s in row["segments"] if s["status"] == "tracked")
        link = f"event-{index:04d}/index.html"
        body.append(f"<tr><td>{index}</td><td>{row['candidate_id']}</td>"
                    f"<td>{row['event_time_s']:.3f}</td>"
                    f"<td>{row['association']['status']}</td>"
                    f"<td>{tracked}/{len(row['segments'])}</td>"
                    f"<td><a href='{link}'>open</a></td></tr>")
    summary = (f"{len(rows)} events; "
               f"{sum(1 for r in rows if any(s['status'] == 'tracked' for s in r['segments']))} "
               "with at least one tracked segment.")
    (output / "index.html").write_text(
        INDEX.replace("__ROWS__", "".join(body)).replace("__SUMMARY__", summary))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--aggregate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--stone-detector-checkpoint", type=Path)
    parser.add_argument("--projection-config", type=Path)
    parser.add_argument("--tracking-progress-dir", type=Path)
    parser.add_argument("--mode", choices=["online", "offline"], default="online")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--expected-decoder-sha")
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        print("Resuming existing dense output", flush=True)
    else:
        args.output.mkdir(parents=True, exist_ok=True)
    aggregate = json.loads(args.aggregate.read_text())
    if aggregate["context"]["source_sha256"] != digest(args.video):
        raise SystemExit("Aggregate and video differ")
    import cv2
    _cap = cv2.VideoCapture(str(args.video))
    fps = float(_cap.get(cv2.CAP_PROP_FPS))
    _cap.release()
    if not fps or fps <= 0:
        raise SystemExit("Cannot read source fps")
    source_end_s = float((aggregate.get("source_interval_s") or [0, 0])[1])
    if args.expected_decoder_sha is None:
        import hashlib
        import cv2
        args.expected_decoder_sha = hashlib.sha256(
            cv2.getBuildInformation().encode()).hexdigest()
    heights = None
    if args.projection_config is not None:
        heights = feature_heights(json.loads(args.projection_config.read_text()))
    stone_detector = None
    if args.stone_detector_checkpoint is not None:
        from prototype.stone_detector import StoneDetector
        stone_detector = StoneDetector(args.stone_detector_checkpoint,
                                       device=args.device, threads=args.threads)
    started = time.perf_counter()
    rows = []
    events = aggregate["events"]
    for index, event in enumerate(events):
        summary_path = args.output / f"event-{index:04d}" / "summary.json"
        if summary_path.exists() and (args.output / f"event-{index:04d}" / "index.html").exists():
            rows.append(global_row(json.loads(summary_path.read_text())))
            print(json.dumps({"resumed": index, "event": event["candidate_id"],
                              "total": len(events)}), flush=True)
            continue
        row = run_event(
            args.video, args.aggregate, args.output, index, event,
            checkpoint=args.checkpoint, mode=args.mode, device=args.device,
            threads=args.threads,
            expected_decoder_sha=args.expected_decoder_sha,
            stone_detector=stone_detector, heights=heights,
            tracking_progress_dir=args.tracking_progress_dir,
            source_end_s=source_end_s, fps=fps)
        rows.append(global_row(row))
        progress = {
            "status": "running",
            "events_completed": index + 1,
            "events_total": len(events),
            "current_event": event["candidate_id"],
            "segments_tracked": sum(
                1 for r in rows for s in r["segments"] if s["status"] == "tracked"),
            "segments_failed": sum(
                1 for r in rows for s in r["segments"] if s["status"] == "failed"),
            "wall_seconds": time.perf_counter() - started,
            "last_event": global_row(row),
        }
        (args.output / "progress.json").write_text(
            json.dumps(progress, indent=2, allow_nan=False) + "\n")
        write_index(args.output, rows)
        print(json.dumps({k: v for k, v in progress.items()
                          if k != "last_event"}), flush=True)
    result = {
        "schema_version": "full-match-dense-development-v1",
        "events": rows,
        "summary": {
            "events": len(rows),
            "segments_tracked": sum(
                1 for r in rows for s in r["segments"] if s["status"] == "tracked"),
            "segments_failed": sum(
                1 for r in rows for s in r["segments"] if s["status"] == "failed"),
            "segments_unavailable": sum(
                1 for r in rows for s in r["segments"] if s["status"] == "unavailable"),
            "provisional_handoffs": sum(
                1 for r in rows if r["association"]["status"] == "provisional"),
            "verified_physical_handoffs": 0,
        },
        "wall_seconds": time.perf_counter() - started,
        "source_sha256": digest(args.video),
        "aggregate_sha256": digest(args.aggregate),
        "checkpoint_sha256": digest(args.checkpoint),
        "physical_identity_verified": False,
        "selection": "all aggregate events",
        "scope": ("Dense CoTracker on every event using the frozen spin implementation; "
                  "per-event viewers; physical identity and metric geometry unverified."),
    }
    (args.output / "result.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n")
    write_index(args.output, rows)
    print(json.dumps(result["summary"]), flush=True)


if __name__ == "__main__":
    main()
