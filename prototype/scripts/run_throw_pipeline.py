"""Route known broadcast layouts to their frozen throw-event adapters.

Unknown or mixed layouts produce a coverage report; --allow-partial can run
supported spans while retaining explicit gaps and boundary uncertainty.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from layout_preflight import frame_evidence, summarize_evidence
from throw_timeline import assemble_timeline
from two_stage_throw_triage import triage_candidates
from scripts.export_candidate_review_union import load_left_sources


def attach_trajectories(video, events_path, output_dir):
    """The default pipeline product includes trajectories and explicit failures."""
    from scripts.complete_throw_trajectories import complete

    return complete(video, events_path, output_dir / "aggregate.json")


def attach_spin_development(args):
    """Optional upstream point-tracking experiment, linked to an existing candidate.

    Leaves aggregate trajectories untouched. Explicit seeds are initialization,
    not an automatic handle detector or evidence of validated physical spin.
    """
    if getattr(args, 'track_throws', False):
        command = [str(ROOT / 'feasibility/scripts/python.sh'), '-m', 'prototype.spin.throws',
                   '--video', str(args.video.resolve()),
                   '--aggregate', str((args.output_dir / 'aggregate.json').resolve()),
                   '--output', str((args.output_dir / 'two-view-tracking').resolve()),
                   '--checkpoint', str(args.spin_checkpoint.resolve()), '--mode', args.spin_mode,
                   '--expected-decoder-sha', hashlib.sha256(cv2.getBuildInformation().encode()).hexdigest()]
        if getattr(args, 'stone_detector_checkpoint', None):
            command += ['--stone-detector-checkpoint', str(args.stone_detector_checkpoint.resolve())]
            command += ['--stone-detector-head', getattr(args,'stone_detector_head','checkpoint'),
                        '--stone-detector-threads', str(getattr(args,'stone_detector_threads',4))]
        if getattr(args, 'stone_colour_config', None):
            command += ['--stone-colour-config', str(args.stone_colour_config.resolve())]
        if getattr(args, 'projection_config', None):
            command += ['--projection-config', str(args.projection_config.resolve())]
        if getattr(args, 'tracking_progress_dir', None):
            command += ['--tracking-progress-dir', str(args.tracking_progress_dir.resolve())]
        if getattr(args, 'throw_tracking_cache', None):
            command += ['--cache-manifest', str(args.throw_tracking_cache.resolve())]
        subprocess.run(command, cwd=ROOT,
                       env={**os.environ, 'CURLING_PYTHON': str(args.spin_python.absolute())}, check=True)
        return
    if args.spin_config is None and not getattr(args, 'track_candidate', None):
        return
    if getattr(args, 'track_candidate', None):
        from spin.pipeline import candidate_config
        generated = args.output_dir / 'point-tracking-initialization.json'
        if generated.exists():
            raise ValueError('Tracking initialization already exists; preserve prior experiment')
        generated.write_text(json.dumps(candidate_config(args.video, args.output_dir / 'aggregate.json',
                                                        args.track_candidate), indent=2)+'\n')
        args.spin_config = generated
    output = args.output_dir / "spin-development"
    command = [
        str(ROOT / "feasibility/scripts/python.sh"),
        str(ROOT / "prototype/scripts/run_spin_analysis.py"),
        "--video", str(args.video.resolve()), "--config", str(args.spin_config.resolve()),
        "--checkpoint", str(args.spin_checkpoint.resolve()),
        "--aggregate", str((args.output_dir / "aggregate.json").resolve()),
        "--output", str(output.resolve()), "--mode", args.spin_mode,
        "--expected-decoder-sha", hashlib.sha256(cv2.getBuildInformation().encode()).hexdigest(),
    ]
    if getattr(args, 'tracking_cache', None):
        command += ['--reuse-result', str(args.tracking_cache.resolve())]
    subprocess.run(command, cwd=ROOT, env={**os.environ, "CURLING_PYTHON": str(args.spin_python.absolute())}, check=True)
    (args.output_dir / "spin-development-link.json").write_text(json.dumps({
        "status": "development_not_validated_spin", "report": "spin-development/index.html",
        "result": "spin-development/result.json", "config_sha256": file_sha256(args.spin_config),
        "aggregate_sha256": file_sha256(args.output_dir / "aggregate.json"),
    }, indent=2) + "\n")


def run_child(script, *args):
    subprocess.run(
        [sys.executable, str(ROOT / "prototype/scripts" / script), *map(str, args)],
        cwd=ROOT,
        check=True,
    )


def attach_source_activity(video, source_sha256, interval, output_dir, timeline_path):
    """Attach an independent image-activity coverage diagnostic to a timeline."""
    audit_path = output_dir / "source-activity-audit.json"
    overlay_path = output_dir / "source-activity-coverage.json"
    if audit_path.exists():
        audit = json.loads(audit_path.read_text())
        if (
            audit.get("source_sha256") != source_sha256
            or audit.get("source_interval_s") != list(interval)
            or audit.get("runner_sha256")
            != file_sha256(ROOT / "prototype/scripts/audit_split_panel_freeze.py")
        ):
            raise ValueError(
                "Existing source-activity audit does not match source, interval or code"
            )
    else:
        run_child(
            "audit_split_panel_freeze.py",
            "--video",
            video,
            "--start",
            interval[0],
            "--end",
            interval[1],
            "--output",
            audit_path,
        )
    if overlay_path.exists():
        overlay = json.loads(overlay_path.read_text())
        expected = {
            "timeline_sha256": file_sha256(timeline_path),
            "activity_audit_sha256": file_sha256(audit_path),
            "overlay_code_sha256": file_sha256(ROOT / "prototype/source_activity_coverage.py"),
            "runner_sha256": file_sha256(
                ROOT / "prototype/scripts/overlay_source_activity_coverage.py"
            ),
        }
        if any(overlay.get(key) != value for key, value in expected.items()):
            raise ValueError("Existing source-activity coverage uses different inputs or code")
    else:
        run_child(
            "overlay_source_activity_coverage.py",
            "--timeline",
            timeline_path,
            "--activity-audit",
            audit_path,
            "--output",
            overlay_path,
        )
    return json.loads(overlay_path.read_text())


def attach_right_view_review(video, source_sha256, output_dir):
    """Preserve right-view motion/entry proposals inside detector-blind spans."""
    overlay_path = output_dir / "source-activity-coverage.json"
    overlay = json.loads(overlay_path.read_text())
    if overlay["source_sha256"] != source_sha256:
        raise ValueError("Right-view probe and source-activity overlay differ")
    if not overlay["newly_unsupported_intervals"]:
        return None
    probe_path = output_dir / "right-motion-in-blind.json"
    triage_path = output_dir / "right-entry-review-in-blind.json"
    if probe_path.exists():
        probe = json.loads(probe_path.read_text())
        expected = {
            "source_sha256": source_sha256,
            "overlay_sha256": file_sha256(overlay_path),
            "tracker_code_sha256": file_sha256(ROOT / "prototype/stone_motion_fallback.py"),
            "frame_normalization_code_sha256": file_sha256(
                ROOT / "prototype/scripts/audit_split_panel_freeze.py"
            ),
            "runner_sha256": file_sha256(
                ROOT / "prototype/scripts/probe_static_left_right_cap_motion.py"
            ),
        }
        if any(probe.get(key) != value for key, value in expected.items()):
            raise ValueError("Existing blind-span right-view probe uses different inputs or code")
    else:
        run_child(
            "probe_static_left_right_cap_motion.py",
            "--video",
            video,
            "--overlay",
            overlay_path,
            "--output",
            probe_path,
        )
    if triage_path.exists():
        triage = json.loads(triage_path.read_text())
        expected = {
            "source_sha256": source_sha256,
            "probe_sha256": file_sha256(probe_path),
            "triage_code_sha256": file_sha256(ROOT / "prototype/right_view_entry_triage.py"),
            "runner_sha256": file_sha256(ROOT / "prototype/scripts/triage_right_static_entries.py"),
        }
        if any(triage.get(key) != value for key, value in expected.items()):
            raise ValueError("Existing blind-span right-entry triage uses different inputs or code")
    else:
        run_child("triage_right_static_entries.py", "--probe", probe_path, "--output", triage_path)
    return json.loads(triage_path.read_text())


def attach_camera_aware_fusion(output_dir, source_sha256, timeline_path):
    """Classify right entries against left coverage without accepting throws."""
    right_path = output_dir / "right-entry-review-in-blind.json"
    coverage_path = output_dir / "source-activity-coverage.json"
    fusion_path = output_dir / "right-entry-camera-fusion.json"
    expected = {
        "source_sha256": source_sha256,
        "right_sha256": file_sha256(right_path),
        "left_sha256": file_sha256(timeline_path),
        "coverage_sha256": file_sha256(coverage_path),
        "partial_state_sha256": None,
        "fusion_code_sha256": file_sha256(ROOT / "prototype/camera_aware_right_fusion.py"),
        "runner_sha256": file_sha256(
            ROOT / "prototype/scripts/export_camera_aware_right_fusion.py"
        ),
    }
    if fusion_path.exists():
        fusion = json.loads(fusion_path.read_text())
        if any(fusion.get(key) != value for key, value in expected.items()):
            raise ValueError("Existing camera-aware fusion uses different inputs or code")
    else:
        run_child(
            "export_camera_aware_right_fusion.py",
            "--right",
            right_path,
            "--left",
            timeline_path,
            "--coverage",
            coverage_path,
            "--output",
            fusion_path,
        )
    return json.loads(fusion_path.read_text())


def attach_candidate_review_union(output_dir, timeline_path):
    """Keep raw left and right-only candidates in one ordered review ledger."""
    output_path = output_dir / "candidate-review-union.json"
    fusion_path = output_dir / "right-entry-camera-fusion.json"
    coverage_path = output_dir / "source-activity-coverage.json"
    if output_path.exists():
        union = json.loads(output_path.read_text())
        timeline = json.loads(timeline_path.read_text())
        _, triage_hashes, reconstructed, raw_hashes = load_left_sources(timeline_path, timeline)
        expected_inputs = {
            "timeline": file_sha256(timeline_path),
            "fusion": file_sha256(fusion_path),
            "coverage": file_sha256(coverage_path),
            "left_triage_by_run": triage_hashes,
            "left_raw_by_run": raw_hashes,
        }
        if reconstructed:
            expected_inputs["left_reconstructed_by_run"] = reconstructed
        if (
            union.get("input_sha256") != expected_inputs
            or union.get("model_code_sha256")
            != file_sha256(ROOT / "prototype/candidate_review_union.py")
            or union.get("runner_sha256")
            != file_sha256(ROOT / "prototype/scripts/export_candidate_review_union.py")
        ):
            raise ValueError("Existing candidate review union uses different inputs or code")
    else:
        run_child(
            "export_candidate_review_union.py",
            "--timeline",
            timeline_path,
            "--fusion",
            fusion_path,
            "--coverage",
            coverage_path,
            "--output",
            output_path,
        )
    return json.loads(output_path.read_text())


def attach_right_partial_boards(video, source_sha256, output_dir):
    """Record timing-bracket-aware partial image caps after right-only entries."""
    fusion_path = output_dir / "right-entry-camera-fusion.json"
    output_path = output_dir / "right-only-partial-caps.json"
    expected = {
        "source_sha256": source_sha256,
        "fusion_sha256": file_sha256(fusion_path),
        "proposal_code_sha256": file_sha256(
            ROOT / "prototype/scripts/probe_static_left_right_cap_motion.py"
        ),
        "frame_normalization_code_sha256": file_sha256(
            ROOT / "prototype/scripts/audit_split_panel_freeze.py"
        ),
        "stable_cap_code_sha256": file_sha256(ROOT / "prototype/right_view_partial_board.py"),
        "cap_set_comparison_code_sha256": file_sha256(
            ROOT / "prototype/right_view_cap_sequence.py"
        ),
        "runner_sha256": file_sha256(ROOT / "prototype/scripts/export_right_only_partial_caps.py"),
    }
    if output_path.exists():
        boards = json.loads(output_path.read_text())
        if any(boards.get(key) != value for key, value in expected.items()):
            raise ValueError("Existing right-only partial boards use different inputs or code")
    else:
        run_child(
            "export_right_only_partial_caps.py",
            "--video",
            video,
            "--fusion",
            fusion_path,
            "--output",
            output_path,
        )
    return json.loads(output_path.read_text())


def attach_candidate_state_handoff(output_dir):
    """Join the ordered review queue to the partial right-only observations."""
    union_path = output_dir / "candidate-review-union.json"
    boards_path = output_dir / "right-only-partial-caps.json"
    output_path = output_dir / "candidate-state-handoff.json"
    expected = {
        "input_sha256": {
            "candidate_review_union": file_sha256(union_path),
            "right_only_partial_caps": file_sha256(boards_path),
        },
        "model_code_sha256": file_sha256(ROOT / "prototype/candidate_state_handoff.py"),
        "runner_sha256": file_sha256(ROOT / "prototype/scripts/export_candidate_state_handoff.py"),
    }
    if output_path.exists():
        handoff = json.loads(output_path.read_text())
        if any(handoff.get(key) != value for key, value in expected.items()):
            raise ValueError("Existing candidate state handoff uses different inputs or code")
    else:
        run_child(
            "export_candidate_state_handoff.py",
            "--union",
            union_path,
            "--right-boards",
            boards_path,
            "--output",
            output_path,
        )
    return json.loads(output_path.read_text())


def attach_right_board_sequence(video, source_sha256, output_dir):
    """Compare adjacent right-only image observations when alignment supports it."""
    union_path = output_dir / "candidate-review-union.json"
    boards_path = output_dir / "right-only-partial-caps.json"
    output_path = output_dir / "right-board-sequence.json"
    expected = {
        "source_sha256": source_sha256,
        "input_sha256": {
            "candidate_review_union": file_sha256(union_path),
            "right_only_partial_caps": file_sha256(boards_path),
        },
        "model_code_sha256": file_sha256(ROOT / "prototype/right_board_sequence.py"),
        "alignment_code_sha256": file_sha256(ROOT / "prototype/right_view_house_alignment.py"),
        "cap_set_comparison_code_sha256": file_sha256(
            ROOT / "prototype/right_view_cap_sequence.py"
        ),
        "frame_normalization_code_sha256": file_sha256(
            ROOT / "prototype/scripts/audit_split_panel_freeze.py"
        ),
        "runner_sha256": file_sha256(ROOT / "prototype/scripts/export_right_board_sequence.py"),
    }
    if output_path.exists():
        sequence = json.loads(output_path.read_text())
        if any(sequence.get(key) != value for key, value in expected.items()):
            raise ValueError("Existing right-board sequence uses different inputs or code")
    else:
        run_child(
            "export_right_board_sequence.py",
            "--video",
            video,
            "--union",
            union_path,
            "--right-boards",
            boards_path,
            "--output",
            output_path,
        )
    return json.loads(output_path.read_text())


def attach_left_candidate_boards(video, source_sha256, output_dir):
    """Sample guarded receiving-view caps after every split-view left proposal."""
    union_path = output_dir / "candidate-review-union.json"
    timeline_path = output_dir / "timeline.json"
    output_path = output_dir / "left-candidate-partial-caps.json"
    expected = {
        "source_sha256": source_sha256,
        "input_sha256": {
            "candidate_review_union": file_sha256(union_path),
            "timeline": file_sha256(timeline_path),
        },
        "runner_sha256": file_sha256(
            ROOT / "prototype/scripts/export_left_candidate_partial_caps.py"
        ),
        "right_sampler_code_sha256": file_sha256(
            ROOT / "prototype/scripts/export_right_only_partial_caps.py"
        ),
        "proposal_code_sha256": file_sha256(
            ROOT / "prototype/scripts/probe_static_left_right_cap_motion.py"
        ),
        "frame_normalization_code_sha256": file_sha256(
            ROOT / "prototype/scripts/audit_split_panel_freeze.py"
        ),
        "stable_cap_code_sha256": file_sha256(ROOT / "prototype/right_view_partial_board.py"),
        "cap_set_comparison_code_sha256": file_sha256(
            ROOT / "prototype/right_view_cap_sequence.py"
        ),
    }
    if output_path.exists():
        boards = json.loads(output_path.read_text())
        if any(boards.get(key) != value for key, value in expected.items()):
            raise ValueError("Existing left candidate boards use different inputs or code")
    else:
        run_child(
            "export_left_candidate_partial_caps.py",
            "--video",
            video,
            "--union",
            union_path,
            "--timeline",
            timeline_path,
            "--output",
            output_path,
        )
    return json.loads(output_path.read_text())


def attach_candidate_state_handoff_v2(output_dir):
    """Join guarded left samples to the existing all-candidate handoff."""
    handoff_path = output_dir / "candidate-state-handoff.json"
    boards_path = output_dir / "left-candidate-partial-caps.json"
    output_path = output_dir / "candidate-state-handoff-v2.json"
    expected = {
        "input_sha256": {
            "candidate_state_handoff": file_sha256(handoff_path),
            "left_candidate_partial_caps": file_sha256(boards_path),
        },
        "model_code_sha256": file_sha256(ROOT / "prototype/candidate_state_handoff_v2.py"),
        "runner_sha256": file_sha256(
            ROOT / "prototype/scripts/export_candidate_state_handoff_v2.py"
        ),
    }
    if output_path.exists():
        handoff = json.loads(output_path.read_text())
        if any(handoff.get(key) != value for key, value in expected.items()):
            raise ValueError("Existing candidate state handoff v2 uses different inputs or code")
    else:
        run_child(
            "export_candidate_state_handoff_v2.py",
            "--handoff",
            handoff_path,
            "--left-boards",
            boards_path,
            "--output",
            output_path,
        )
    return json.loads(output_path.read_text())


def attach_candidate_image_board_sequence(video, source_sha256, output_dir):
    """Compare adjacent all-candidate partial boards with sampled image alignment."""
    handoff_path = output_dir / "candidate-state-handoff-v2.json"
    output_path = output_dir / "candidate-image-board-sequence.json"
    expected = {
        "source_sha256": source_sha256,
        "handoff_sha256": file_sha256(handoff_path),
        "model_code_sha256": file_sha256(ROOT / "prototype/candidate_image_board_sequence.py"),
        "alignment_code_sha256": file_sha256(ROOT / "prototype/right_view_house_alignment.py"),
        "cap_set_comparison_code_sha256": file_sha256(
            ROOT / "prototype/right_view_cap_sequence.py"
        ),
        "frame_normalization_code_sha256": file_sha256(
            ROOT / "prototype/scripts/audit_split_panel_freeze.py"
        ),
        "runner_sha256": file_sha256(
            ROOT / "prototype/scripts/export_candidate_image_board_sequence.py"
        ),
    }
    if output_path.exists():
        sequence = json.loads(output_path.read_text())
        if any(sequence.get(key) != value for key, value in expected.items()):
            raise ValueError(
                "Existing candidate image board sequence uses different inputs or code"
            )
    else:
        run_child(
            "export_candidate_image_board_sequence.py",
            "--video",
            video,
            "--handoff",
            handoff_path,
            "--output",
            output_path,
        )
    return json.loads(output_path.read_text())


def attach_candidate_house_ellipse(video, source_sha256, output_dir):
    """Give usable cap pixels a guarded image-relative house reference."""
    handoff_path = output_dir / "candidate-state-handoff-v2.json"
    output_path = output_dir / "candidate-house-ellipse.json"
    expected = {
        "source_sha256": source_sha256,
        "handoff_sha256": file_sha256(handoff_path),
        "paint_mask_code_sha256": file_sha256(ROOT / "prototype/split_house_reference.py"),
        "model_code_sha256": file_sha256(ROOT / "prototype/split_house_ellipse_v2.py"),
        "frame_normalization_code_sha256": file_sha256(
            ROOT / "prototype/scripts/audit_split_panel_freeze.py"
        ),
        "runner_sha256": file_sha256(ROOT / "prototype/scripts/export_candidate_house_ellipse.py"),
    }
    if output_path.exists():
        result = json.loads(output_path.read_text())
        if any(result.get(key) != value for key, value in expected.items()):
            raise ValueError("Existing candidate house ellipse uses different inputs or code")
    else:
        run_child(
            "export_candidate_house_ellipse.py",
            "--video",
            video,
            "--handoff",
            handoff_path,
            "--output",
            output_path,
        )
    return json.loads(output_path.read_text())


def write_timeline(preflight, completed, output_dir):
    timeline = assemble_timeline(preflight, completed)
    timeline["assembler_sha256"] = file_sha256(ROOT / "prototype/throw_timeline.py")
    timeline["preflight_artifact_sha256"] = file_sha256(output_dir / "preflight.json")
    timeline_path = output_dir / "timeline.json"
    timeline_text = json.dumps(timeline, indent=2) + "\n"
    if timeline_path.exists():
        if timeline_path.read_text() != timeline_text:
            raise ValueError("Existing timeline differs from verified adapter artifacts")
    else:
        timeline_path.write_text(timeline_text)
    return timeline, timeline_path


def read_matching_artifact(path, source_id, digest, interval, model_path=None):
    result = json.loads(path.read_text())
    if (
        result.get("source_id") != source_id
        or result.get("source_sha256") != digest
        or result.get("source_interval_s") != list(interval)
    ):
        raise ValueError(f"Existing artifact does not match requested source/interval: {path}")
    if model_path and result.get("model_sha256") != file_sha256(model_path):
        raise ValueError(f"Existing artifact uses different model code: {path}")
    return result


def require_code_hash(artifact, field, code_path, artifact_path):
    if artifact.get(field) != file_sha256(code_path):
        raise ValueError(f"Existing artifact uses different {field}: {artifact_path}")


def sample_layout(video, start_s, end_s, chunk_s=300):
    cap = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps if fps > 0 else 0
    if not 0 <= start_s < end_s <= duration:
        cap.release()
        raise ValueError("Invalid interval or unreadable video")
    step = min(10.0, max(1.0, (end_s - start_s) / 12))
    samples = []
    t = float(start_s)
    while t < end_s:
        cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
        ok, frame = cap.read()
        if not ok:
            cap.release()
            raise RuntimeError(f"Layout frame decode failed at {t:.3f} s")
        samples.append({"time_s": round(t, 3), **frame_evidence(frame)})
        t += step
    cap.release()
    return summarize_evidence(samples, start_s, end_s, chunk_s=chunk_s), samples, duration


def run_adapter(
    video, source_id, digest, layout, start, end, output_dir, *, resume=False, preflight_path=None
):
    """Run the existing layout-specific adapter in one distinct output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    if layout == "split_2024":
        raw = output_dir / "raw.json"
        motion = output_dir / "motion.json"
        events = output_dir / "events.json"
        if resume and raw.exists():
            existing_raw = read_matching_artifact(
                raw, source_id, digest, [start, end], ROOT / "prototype/span_passage_detection.py"
            )
            require_code_hash(
                existing_raw, "runner_sha256", ROOT / "prototype/scripts/run_span_probe.py", raw
            )
        else:
            run_child(
                "run_span_probe.py",
                "--video",
                video,
                "--source-id",
                source_id,
                "--start",
                start,
                "--end",
                end,
                "--output",
                raw,
            )
        if resume and motion.exists():
            measured = read_matching_artifact(motion, source_id, digest, [start, end])
            if measured.get("input_sha256") != file_sha256(raw):
                raise ValueError("Existing motion artifact does not match raw candidates")
            require_code_hash(
                measured,
                "feature_code_sha256",
                ROOT / "prototype/passage_motion_context.py",
                motion,
            )
            require_code_hash(
                measured,
                "runner_sha256",
                ROOT / "prototype/scripts/measure_passage_motion_context.py",
                motion,
            )
        else:
            run_child(
                "measure_passage_motion_context.py",
                "--video",
                video,
                "--candidates",
                raw,
                "--output",
                motion,
            )
        if resume and events.exists():
            confirmed = read_matching_artifact(
                events,
                source_id,
                digest,
                [start, end],
                ROOT / "prototype/span_context_confirmation.py",
            )
            if confirmed.get("input_sha256") != file_sha256(raw) or confirmed.get(
                "motion_sha256"
            ) != file_sha256(motion):
                raise ValueError("Existing confirmed events do not match input artifacts")
            require_code_hash(
                confirmed,
                "runner_sha256",
                ROOT / "prototype/scripts/confirm_span_context.py",
                events,
            )
        else:
            run_child(
                "confirm_span_context.py",
                "--candidates",
                raw,
                "--motion",
                motion,
                "--output",
                events,
            )
        # The confirmed event artifact remains the frozen scoring output.
        # A parallel lossless ledger preserves all raw proposals for review.
        raw_data = json.loads(raw.read_text())
        confirmed_data = json.loads(events.read_text())
        triaged = triage_candidates(raw_data["events"], [("span_context", confirmed_data)])
        triage_path = output_dir / "triage.json"
        triage_document = {
            "status": "candidate_triage_not_physical_event_validation",
            "source_id": source_id,
            "source_sha256": digest,
            "source_interval_s": [start, end],
            "raw_sha256": file_sha256(raw),
            "confirmation_sha256": file_sha256(events),
            "triage_code_sha256": file_sha256(ROOT / "prototype/two_stage_throw_triage.py"),
            "counts": triaged["counts"],
            "proposals": triaged["proposals"],
            "limitations": [
                "Review proposals are not confirmed throws and must not be silently discarded.",
                "The span-context gate is development-fitted and covers only the known 2024 split-screen layout.",
                "First observed motion and passage times are not exact physical release times.",
            ],
        }
        triage_text = json.dumps(triage_document, indent=2) + "\n"
        if triage_path.exists():
            if triage_path.read_text() != triage_text:
                raise ValueError(
                    "Existing triage differs from verified proposal and confirmation artifacts"
                )
        else:
            triage_path.write_text(triage_text)
        if preflight_path is not None:
            camera_motion = output_dir / "candidate-camera-motion.json"
            if resume and camera_motion.exists():
                sidecar = read_matching_artifact(camera_motion, source_id, digest, [start, end])
                if sidecar.get("input_sha256") != {
                    "raw": file_sha256(raw),
                    "preflight": file_sha256(preflight_path),
                }:
                    raise ValueError("Existing candidate motion uses different inputs")
                code = sidecar.get("code_sha256", {})
                for name, path in {
                    "candidate": ROOT / "prototype/candidate_camera_motion.py",
                    "router": ROOT / "prototype/layout_camera_motion.py",
                    "lowres_adapter": ROOT / "prototype/lowres_split_panel_camera_registration.py",
                    "split_registration": ROOT / "prototype/split_panel_camera_registration.py",
                    "runner": ROOT / "prototype/scripts/measure_candidate_camera_motion.py",
                }.items():
                    if code.get(name) != file_sha256(path):
                        raise ValueError(f"Existing candidate motion uses different {name} code")
            else:
                run_child(
                    "measure_candidate_camera_motion.py",
                    "--video",
                    video,
                    "--raw",
                    raw,
                    "--preflight",
                    preflight_path,
                    "--output",
                    camera_motion,
                )
    elif layout == "beijing_2022":
        if int(start) != start or int(end) != end:
            raise ValueError("Beijing adapter requires integer-second boundaries")
        full_output = output_dir / "full-shot"
        run_child(
            "run_full_shot_evidence.py",
            "--video",
            video,
            "--source-id",
            source_id,
            "--start",
            int(start),
            "--end",
            int(end),
            "--origin-model",
            ROOT
            / "validation/curlobserver-learned-probe/shot-origin-pair-v1/model-excluding-swiss-dev.npz",
            "--learned-model",
            ROOT / "validation/curlobserver-learned-probe/model-v1/model.npz",
            "--output",
            full_output,
        )
        ledger_path = full_output / "candidate-event-ledger.json"
        ledger = json.loads(ledger_path.read_text())
        adapted = {
            **ledger,
            "source_id": source_id,
            "events": [
                {
                    **row,
                    "id": row["candidate_id"],
                    "crossing_time_s": row["observation_anchor_s"],
                    "motion_review_path": str(
                        (full_output / "shot-review/manifest.json").resolve()
                    ),
                }
                for row in ledger["events"]
            ],
        }
        events = output_dir / "events.json"
        adapted["full_shot_ledger_sha256"] = file_sha256(ledger_path)
        events.write_text(json.dumps(adapted, indent=2) + "\n")

    else:
        raise ValueError("Unsupported adapter layout")
    return events, json.loads(events.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--start", required=True, type=float)
    parser.add_argument("--end", required=True, type=float)
    parser.add_argument(
        "--layout-chunk-s",
        type=float,
        default=300,
        help="Duration of each preflight decision window (default: 300 seconds)",
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--spin-config", type=Path, help="Optional candidate-linked development point-tracking configuration")
    parser.add_argument("--track-candidate", help="Automatically seed upstream point tracking from an existing split segment ID; no manual points")
    parser.add_argument("--stone-detector-backend", choices=["pytorch", "openvino_gpu"], default="pytorch", help="Explicit learned-event detector runtime; GPU never silently falls back to CPU")
    parser.add_argument("--stone-detector-export", type=Path, help="Versioned OpenVINO export directory for --stone-detector-backend openvino_gpu")
    parser.add_argument("--event-line-config", type=Path, help="Configured-line learned event mode; select --events-only or --track-throws")
    parser.add_argument("--events-only", action="store_true", help="Run learned line-event stage without legacy cap-trajectory attachment")
    parser.add_argument("--match-state-config", type=Path, help="Development board/score observations alongside learned line events; does not certify identity or replace dense CoTracker")
    parser.add_argument("--detection-cache", type=Path, help="Reuse immutable, exact-contract learned detections from a previous run; reconstruct tracking in the current run")
    parser.add_argument("--detection-cache-prefix-samples", type=int, help="Reuse only this verified committed prefix, then run fresh detection")
    parser.add_argument("--track-throws", action="store_true", help="Dense tracking of both split-camera segments for every event; provisional handoffs retained")
    parser.add_argument("--stone-detector-checkpoint", type=Path, help="Learned stone scene/board detector; use a Python environment with both detector and CoTracker dependencies")
    parser.add_argument('--stone-detector-head',choices=['checkpoint','end2end','conventional'],default='checkpoint')
    parser.add_argument('--stone-detector-threads',type=int,default=4)
    parser.add_argument("--stone-colour-config", type=Path, help="Optional OpenCLIP snapshot colour predictions; requires --track-throws and a learned detector")
    parser.add_argument('--score-layout-memory', action='store_true', help='Development offline score/layout evidence and synchronized viewer; requires learned line events and match-state config')
    parser.add_argument("--projection-config", type=Path, help="JSON feature heights in metres for dense trajectories and snapshots")
    parser.add_argument("--throw-tracking-cache", type=Path, help="JSON mapping segment IDs to hash-checked dense result caches")
    parser.add_argument('--tracking-progress-dir', type=Path, help='Exact-contract online CPU CoTracker progress checkpoints; resume interrupted inference')
    parser.add_argument("--tracking-cache", type=Path, help="Reuse matching upstream point predictions for development analysis")
    parser.add_argument("--spin-checkpoint", type=Path, default=ROOT / "models/cotracker3/scaled_online.pth")
    parser.add_argument("--spin-mode", choices=["online", "offline"], default="online")
    parser.add_argument("--spin-python", type=Path, default=ROOT / ".venv-tracking/bin/python")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument(
        "--resume", action="store_true", help="Reuse a matching preflight and adapter stages"
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Process supported runs and emit a gap-aware timeline when the full interval is mixed",
    )
    parser.add_argument(
        "--audit-source-activity",
        action="store_true",
        help="For split-view runs, report long active-right/static-left detector-blind spans",
    )
    parser.add_argument(
        "--probe-blind-right",
        action="store_true",
        help="Also save unconfirmed right-view motion and entry proposals in blind spans",
    )
    parser.add_argument(
        "--observe-blind-right-boards",
        action="store_true",
        help="Also sample timing-bracket-aware partial caps after right-only entries",
    )
    parser.add_argument(
        "--compare-blind-right-boards",
        action="store_true",
        help="Also compare adjacent partial caps with sampled house alignment",
    )
    parser.add_argument(
        "--observe-left-candidate-boards",
        action="store_true",
        help="Also sample guarded receiving-view caps after all split-view left proposals",
    )
    parser.add_argument(
        "--compare-all-candidate-boards",
        action="store_true",
        help="Also compare adjacent all-candidate partial boards when image alignment supports it",
    )
    parser.add_argument(
        "--fit-candidate-house-ellipse",
        action="store_true",
        help="Also fit guarded image-relative receiving-house ellipses for usable caps",
    )
    args = parser.parse_args()
    if args.detection_cache_prefix_samples is not None and (not args.detection_cache or args.detection_cache_prefix_samples<=0):
        parser.error('--detection-cache-prefix-samples requires a cache and a positive sample count')
    if args.detection_cache and not args.event_line_config:
        parser.error('--detection-cache requires learned line-event mode')
    if args.match_state_config and not args.event_line_config:
        parser.error('--match-state-config requires learned line-event mode')
    if args.event_line_config or args.events_only:
        if not (args.event_line_config and args.stone_detector_checkpoint and args.events_only!=args.track_throws):
            parser.error('Learned line mode requires a detector checkpoint and exactly one of --events-only / --track-throws')
        if args.spin_config or args.track_candidate or args.resume or args.preflight_only or args.audit_source_activity or args.projection_config:
            parser.error('Learned line mode cannot use legacy routing or cap-specific overrides; configure feature heights in --match-state-config')
        if args.track_throws:
            if not args.match_state_config:parser.error('Learned dense tracking requires --match-state-config')
            learned_state_config=json.loads(args.match_state_config.read_text())
            handoff_method=learned_state_config.get('handoff_method')
            if handoff_method=='observed_motion_bidirectional_hog_crossing_development':
                import math
                hog=learned_state_config.get('local_hog_y_m',{})
                if set(hog)!={'left','right'} or any(not isinstance(v,(int,float)) or not math.isfinite(v) or v==0 for v in hog.values()):
                    parser.error('Directional association requires finite nonzero local_hog_y_m for both calibration coordinate systems')
            elif handoff_method=='unique_temporal_hog_crossing_development':
                if learned_state_config.get('camera_roles')!={'left':'departure','right':'receiving'}:
                    parser.error('Legacy handoff requires explicitly configured left departure / right receiving roles')
            else:
                parser.error('Explicitly select a supported development handoff method; physical identity is not verified')

    if args.stone_detector_backend == 'openvino_gpu':
        if not args.event_line_config or not args.stone_detector_export:
            parser.error('OpenVINO GPU requires --event-line-config and --stone-detector-export')
    elif args.stone_detector_export:
        parser.error('--stone-detector-export requires --stone-detector-backend openvino_gpu')
    if args.stone_detector_threads<1:
        parser.error('--stone-detector-threads must be positive')
    if args.stone_colour_config and not (args.track_throws and args.stone_detector_checkpoint):
        parser.error('--stone-colour-config requires --track-throws and --stone-detector-checkpoint')
    if args.projection_config and not args.track_throws:
        parser.error('--projection-config requires --track-throws')
    if args.stone_detector_checkpoint and not (args.track_throws or args.events_only):
        parser.error('--stone-detector-checkpoint requires --track-throws')
    if args.stone_detector_checkpoint and args.spin_python == ROOT / '.venv-tracking/bin/python':
        args.spin_python = ROOT / '.venv-detector/bin/python'
    if args.track_throws and (args.spin_config is not None or args.track_candidate or args.tracking_cache):
        parser.error('--track-throws cannot be combined with single-segment tracking options')
    if args.throw_tracking_cache and not args.track_throws:
        parser.error('--throw-tracking-cache requires --track-throws')
    if args.spin_config is not None and args.track_candidate:
        parser.error('Choose --spin-config or --track-candidate, not both')
    if args.probe_blind_right and not args.audit_source_activity:
        parser.error("--probe-blind-right requires --audit-source-activity")
    if args.observe_blind_right_boards and not args.probe_blind_right:
        parser.error("--observe-blind-right-boards requires --probe-blind-right")
    if args.compare_blind_right_boards and not args.observe_blind_right_boards:
        parser.error("--compare-blind-right-boards requires --observe-blind-right-boards")
    if args.observe_left_candidate_boards and not args.observe_blind_right_boards:
        parser.error("--observe-left-candidate-boards requires --observe-blind-right-boards")
    if args.compare_all_candidate_boards and not args.observe_left_candidate_boards:
        parser.error("--compare-all-candidate-boards requires --observe-left-candidate-boards")
    if args.fit_candidate_house_ellipse and not args.observe_left_candidate_boards:
        parser.error("--fit-candidate-house-ellipse requires --observe-left-candidate-boards")
    if args.resume:
        if not (args.output_dir / "preflight.json").exists():
            parser.error("Resume requires an existing preflight.json")
    elif args.output_dir.exists():
        parser.error("Output directory exists; preserve prior results")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    digest = file_sha256(args.video)
    if (
        digest == reserved["source_sha256"]
        or args.video.resolve() == (ROOT / "validation/unseen-end/source.mp4").resolve()
        or any(args.source_id in row["video_url"] for row in reserved["reserved_rows"])
    ):
        parser.error("This source is reserved for independent evaluation")
    if args.score_layout_memory and not (args.event_line_config and args.match_state_config):
        parser.error('--score-layout-memory requires --event-line-config and --match-state-config')
    if args.event_line_config:
        sys.path.insert(0, str(ROOT))
        from prototype.learned_event_pipeline import run as run_line_events
        result = run_line_events(args.video, args.output_dir, args.event_line_config,
                                 args.stone_detector_checkpoint, start=args.start, end=args.end,
                                 source_id=args.source_id, match_state_config=args.match_state_config,detection_cache=args.detection_cache,
                                 detection_cache_prefix_samples=args.detection_cache_prefix_samples,
                                 detector_backend=args.stone_detector_backend,detector_export=args.stone_detector_export,
                                 detector_head=args.stone_detector_head,detector_threads=args.stone_detector_threads)
        if args.score_layout_memory:
            from prototype.match_state_timeline import run as assemble_match_state
            state_config = json.loads(args.match_state_config.read_text())
            assemble_match_state(args.output_dir, args.output_dir/'score-observations.jsonl',
                                 args.output_dir/'match-state', state_config['scoreboard_team_labels'],
                                 score_layout_memory=True)
            from prototype.match_observation_report import render as render_match_state
            render_match_state(args.output_dir, args.video, result['events'])
        if args.track_throws:
            from prototype.learned_event_aggregate import build as build_learned_aggregate
            from prototype.body_localization import feature_heights
            if learned_state_config['handoff_method']=='observed_motion_bidirectional_hog_crossing_development':
                from prototype.directional_event_aggregate import build as build_directional_aggregate
                build_directional_aggregate(args.video,args.output_dir,args.output_dir/'aggregate.json',
                    hog_y_by_panel=learned_state_config['local_hog_y_m'])
            else:
                build_learned_aggregate(args.video,args.output_dir,args.output_dir/'aggregate.json',
                    camera_roles=learned_state_config['camera_roles'],receiving_hog_association=True)
            from prototype.match_observation_report import render as render_match_observations
            render_match_observations(args.output_dir,args.video,result['events'])
            args.projection_config=args.output_dir/'resolved-projection-heights.json'
            args.projection_config.write_text(json.dumps(feature_heights(learned_state_config.get('feature_heights_m')),indent=2))
            attach_spin_development(args)
            page=args.output_dir/'index.html'
            page.write_text(page.read_text().replace('No trajectory attachment in this event-stage mode.','Dense tracking is attached in the linked development report; physical identity remains unverified.').replace('<select id="events">','<p><a href="two-view-tracking/index.html">Dense two-view tracking and post-throw observations (development)</a></p><select id="events">'))
            print(json.dumps({'event_crossings':len(result['events']),'status':'development_dense_tracking_attached',
                              'physical_identity_verified':False,'report':str(args.output_dir/'two-view-tracking/index.html')}))
            return
        print(json.dumps({'event_crossings': len(result['events']), 'status': result['status']}))
        return
    if args.layout_chunk_s <= 0:
        parser.error("Layout chunk duration must be positive")
    if args.resume:
        preflight = json.loads((args.output_dir / "preflight.json").read_text())
        if (
            preflight.get("source_id") != args.source_id
            or preflight.get("source_sha256") != digest
            or preflight.get("source_interval_s") != [args.start, args.end]
            or preflight.get("layout_chunk_s") != args.layout_chunk_s
            or preflight.get("preflight_sha256")
            != file_sha256(ROOT / "prototype/layout_preflight.py")
        ):
            parser.error("Existing preflight does not match source, interval or layout rules")
        route = preflight
    else:
        route, samples, duration = sample_layout(
            args.video, args.start, args.end, chunk_s=args.layout_chunk_s
        )
        args.output_dir.mkdir(parents=True)
        preflight = {
            "source_id": args.source_id,
            "source_sha256": digest,
            "source_interval_s": [args.start, args.end],
            "source_duration_s": duration,
            "layout_chunk_s": args.layout_chunk_s,
            "preflight_sha256": file_sha256(ROOT / "prototype/layout_preflight.py"),
            "runner_sha256": file_sha256(__file__),
            "layout": route["layout"],
            "chunks": route["chunks"],
            "runs": route["runs"],
            "coverage_gaps_s": route["coverage_gaps_s"],
            "samples": samples,
            "limitations": [
                "Layout routing was fitted to three 2024 split-screen and three 2022 Beijing recordings.",
                "Sparse preflight samples do not prove continuous camera coverage.",
                "Layout recognition does not validate event precision, recall, or physical throw boundaries.",
            ],
        }
        (args.output_dir / "preflight.json").write_text(json.dumps(preflight, indent=2) + "\n")
    if args.preflight_only:
        print(json.dumps({"layout": route["layout"], "events": None}))
        return
    if route["layout"] != "unknown":
        artifact, result = run_adapter(
            args.video,
            args.source_id,
            digest,
            route["layout"],
            args.start,
            args.end,
            args.output_dir,
            resume=args.resume,
            preflight_path=args.output_dir / "preflight.json",
        )
        activity = None
        right_review = None
        timeline, timeline_path = write_timeline(
            preflight,
            [(route["runs"][0], result, artifact.relative_to(args.output_dir))],
            args.output_dir,
        )
        if args.audit_source_activity and route["layout"] == "split_2024":
            activity = attach_source_activity(
                args.video, digest, [args.start, args.end], args.output_dir, timeline_path
            )
            if args.probe_blind_right:
                right_review = attach_right_view_review(args.video, digest, args.output_dir)
                if right_review is not None:
                    attach_camera_aware_fusion(args.output_dir, digest, timeline_path)
                    attach_candidate_review_union(args.output_dir, timeline_path)
                    if args.observe_blind_right_boards:
                        attach_right_partial_boards(args.video, digest, args.output_dir)
                        attach_candidate_state_handoff(args.output_dir)
                        if args.compare_blind_right_boards:
                            attach_right_board_sequence(args.video, digest, args.output_dir)
                        if args.observe_left_candidate_boards:
                            attach_left_candidate_boards(args.video, digest, args.output_dir)
                            attach_candidate_state_handoff_v2(args.output_dir)
                            if args.compare_all_candidate_boards:
                                attach_candidate_image_board_sequence(
                                    args.video, digest, args.output_dir
                                )
                            if args.fit_candidate_house_ellipse:
                                attach_candidate_house_ellipse(args.video, digest, args.output_dir)
        aggregate = attach_trajectories(args.video, timeline_path, args.output_dir)
        attach_spin_development(args)
        print(
            json.dumps(
                {
                    "layout": route["layout"],
                    "events": len(result["events"]),
                    "aggregate": aggregate["summary"],
                    "detector_blind_seconds": activity["newly_unsupported_seconds"]
                    if activity
                    else None,
                    "right_entry_review_proposals": sum(
                        row["entry_review_count"] for row in right_review["intervals"]
                    )
                    if right_review
                    else None,
                }
            )
        )
        return
    if not args.allow_partial:
        print(json.dumps({"layout": "unknown", "events": None}))
        return
    completed = []
    for index, run in enumerate(route["runs"], 1):
        if run["layout"] == "unknown":
            continue
        start, end = run["interval_s"]
        artifact, result = run_adapter(
            args.video,
            args.source_id,
            digest,
            run["layout"],
            start,
            end,
            args.output_dir / f"run-{index:02}",
            resume=args.resume,
            preflight_path=args.output_dir / "preflight.json",
        )
        completed.append((run, result, artifact.relative_to(args.output_dir)))
    timeline, timeline_path = write_timeline(preflight, completed, args.output_dir)
    activity = None
    right_review = None
    if args.audit_source_activity and any(run["layout"] == "split_2024" for run in route["runs"]):
        activity = attach_source_activity(
            args.video, digest, [args.start, args.end], args.output_dir, timeline_path
        )
        if args.probe_blind_right:
            right_review = attach_right_view_review(args.video, digest, args.output_dir)
            if right_review is not None:
                attach_camera_aware_fusion(args.output_dir, digest, timeline_path)
                attach_candidate_review_union(args.output_dir, timeline_path)
                if args.observe_blind_right_boards:
                    attach_right_partial_boards(args.video, digest, args.output_dir)
                    attach_candidate_state_handoff(args.output_dir)
                    if args.compare_blind_right_boards:
                        attach_right_board_sequence(args.video, digest, args.output_dir)
                    if args.observe_left_candidate_boards:
                        attach_left_candidate_boards(args.video, digest, args.output_dir)
                        attach_candidate_state_handoff_v2(args.output_dir)
                        if args.compare_all_candidate_boards:
                            attach_candidate_image_board_sequence(
                                args.video, digest, args.output_dir
                            )
                        if args.fit_candidate_house_ellipse:
                            attach_candidate_house_ellipse(args.video, digest, args.output_dir)
    aggregate = attach_trajectories(args.video, timeline_path, args.output_dir)
    attach_spin_development(args)
    print(
        json.dumps(
            {
                "layout": "unknown",
                "status": timeline["status"],
                "observed_events": timeline["observed_event_count"],
                "aggregate": aggregate["summary"],
                "coverage_gaps": len(timeline["coverage_gaps_s"]),
                "detector_blind_seconds": activity["newly_unsupported_seconds"]
                if activity
                else None,
                "right_entry_review_proposals": sum(
                    row["entry_review_count"] for row in right_review["intervals"]
                )
                if right_review
                else None,
            }
        )
    )


if __name__ == "__main__":
    main()
