"""Recompute recorded experiments in an isolated copy, without reusing output caches.

Run with a newly installed requirements-dev.txt environment. Original files stay intact.
Saved source media, review images, annotations and frozen protocols are required inputs.
"""

from pathlib import Path
import argparse
import concurrent.futures
import csv
import hashlib
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = [
    "feasibility/results/summary.json",
    "feasibility/results/homographies.json",
    *[
        f"feasibility/results/{n}.csv"
        for n in (
            "calibration_metrics",
            "landmark_errors",
            "measured_stones",
            "stone_comparisons",
            "repeat_zoom_consistency",
        )
    ],
    "prototype/stone-accuracy/results.json",
    "prototype/body-localization/results.json",
    "prototype/body-localization/transfer-check.json",
    "prototype/vision/results.json",
    "prototype/vision/evaluation.json",
    "prototype/vision/development-evaluation.json",
    "prototype/rectification/calibration.json",
    "prototype/rectification/audit.json",
    "prototype/rectification/timeline.json",
    "prototype/continuous/timeline.json",
    "prototype/continuous/diagnostics.json",
    "prototype/body-localization/video-timeline.json",
    "prototype/throw-analysis/predictions.json",
    "prototype/throw-analysis/evaluation.json",
    "prototype/throw-analysis/target-analysis.json",
    "prototype/trajectory-accuracy/results.json",
    "prototype/pre-gate-audit/results.json",
    "prototype/throw-segments/manifest.json",
    "prototype/throw-segments/results.json",
    "prototype/cross-view/results.json",
    *[f"prototype/throw-segments/T{i:02}.json" for i in range(1, 17)],
    *[f"prototype/cross-view/T{i:02}-departure.json" for i in range(1, 17)],
]
# These fields describe execution duration or changing orchestration provenance, not
# detector observations or metric values. Their raw files/hashes remain in the report.
METADATA_KEYS = {"processing_seconds", "cache_context", "script_sha256", "input_sha256"}


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def differences(a, b, path="$", limit=12):
    """Compare content with a declared 1e-9 absolute/relative numeric tolerance."""
    if isinstance(a, dict) and isinstance(b, dict):
        ka, kb = set(a) - METADATA_KEYS, set(b) - METADATA_KEYS
        out = [] if ka == kb else [f"{path}: keys differ {sorted(ka ^ kb)}"]
        for k in sorted(ka & kb):
            out.extend(differences(a[k], b[k], f"{path}.{k}", limit))
            if len(out) >= limit:
                break
        return out[:limit]
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{path}: length {len(a)} -> {len(b)}"]
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out.extend(differences(x, y, f"{path}[{i}]", limit))
            if len(out) >= limit:
                break
        return out[:limit]
    if type(a) in (float, int) and type(b) in (float, int):
        return [] if math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9) else [f"{path}: {a} -> {b}"]
    return [] if a == b else [f"{path}: {str(a)[:120]} -> {str(b)[:120]}"]


def load(path):
    if path.suffix == ".json":
        return json.loads(path.read_text())
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        for k, value in row.items():
            try:
                row[k] = float(value)
            except (ValueError, TypeError):
                pass
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workdir", type=Path, required=True, help="New, nonexistent directory")
    parser.add_argument("--report-dir", type=Path, default=ROOT / "validation/full-reproduction")
    args = parser.parse_args()
    work = args.workdir.resolve()
    report_dir = args.report_dir.resolve()
    if work.exists() or work == ROOT or ROOT in work.parents:
        parser.error("--workdir must be a new directory outside this project")
    missing = [relative for relative in OUTPUTS if not (ROOT / relative).is_file()]
    if missing:
        parser.error("Recorded baseline outputs are required for comparison: " + ", ".join(missing))
    report_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "python": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "isolated_python_environment": sys.prefix != sys.base_prefix,
        "isolated_workspace": str(work),
        "numeric_tolerance": {"absolute": 1e-9, "relative": 1e-9},
        "ignored_comparison_metadata": sorted(METADATA_KEYS),
        "scope": "Saved input media and annotations; no source redownload or manual relabelling.",
        "steps": [],
        "comparisons": [],
        "passed": False,
    }
    lock = threading.Lock()

    def save():
        (report_dir / "report.json").write_text(json.dumps(report, indent=2))

    print("Copying isolated workspace", flush=True)
    shutil.copytree(
        ROOT,
        work,
        ignore=shutil.ignore_patterns(
            ".git",
            ".venv",
            "__pycache__",
            ".ruff_cache",
            "validation",
            "dist",
            "uploads",
        ),
    )
    baseline = {}
    for relative in OUTPUTS:
        p = work / relative
        if p.exists():
            baseline[relative] = (load(p), sha(p))
            p.unlink()
    # Also clear presentation artifacts produced by the steps below.
    for relative in ("prototype/rectification/left.mp4", "prototype/rectification/right.mp4"):
        (work / relative).unlink(missing_ok=True)
    report["cleared_outputs"] = sorted(baseline)
    inputs = []
    for folder in (
        "feasibility/annotations",
        "feasibility/frames",
        "prototype/vision/annotations",
        "prototype/vision/frames",
    ):
        inputs.extend(p for p in (work / folder).rglob("*") if p.is_file())
    inputs.extend(
        work / p
        for p in (
            "prototype/sources/canada-korea-2024-360p.mp4",
            "prototype/throw-analysis/end3.mp4",
            "prototype/continuous/clip.mp4",
            "feasibility/sources/owg2018_final_records.csv",
            "prototype/stone-accuracy/protocol.json",
            "prototype/throw-analysis/reference.json",
            "prototype/trajectory-accuracy/reference.json",
        )
    )
    report["input_sha256"] = {str(p.relative_to(work)): sha(p) for p in inputs}
    source = json.loads((work / "prototype/throw-analysis/source.json").read_text())
    for key in ("display_video", "inference_video"):
        spec = source[key]
        p = (work / "prototype/throw-analysis" / spec["file"]).resolve()
        if sha(p) != spec["sha256"]:
            raise ValueError(f"Source hash mismatch: {p}")
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("CURLING_BROWSER_PYTHON", None)
    env["PYTHONNOUSERSITE"] = "1"
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    save()

    def run(script, *arguments):
        name = Path(script).stem + ("-check" if "--include-check" in arguments else "")
        command = [sys.executable, script, *arguments]
        print("START", name, flush=True)
        started = time.monotonic()
        with (report_dir / f"{name}.txt").open("w") as f:
            proc = subprocess.run(
                command, cwd=work, env=env, stdout=f, stderr=subprocess.STDOUT, timeout=7200
            )
        with lock:
            report["steps"].append(
                {
                    "name": name,
                    "command": command[1:],
                    "returncode": proc.returncode,
                    "seconds": round(time.monotonic() - started, 2),
                }
            )
            save()
        print("DONE", name, proc.returncode, flush=True)
        if proc.returncode:
            raise RuntimeError(f"Failed {name}; see {report_dir / (name + '.txt')}")

    def proto(name, *args):
        run(f"prototype/scripts/{name}.py", *args)

    subprocess.run([sys.executable, "-m", "pip", "check"], env=env, check=True)
    (report_dir / "installed.txt").write_bytes(
        subprocess.check_output([sys.executable, "-m", "pip", "freeze"], env=env)
    )
    (report_dir / "ffmpeg.txt").write_bytes(
        subprocess.check_output(["ffmpeg", "-version"], env=env)
    )
    proto("calibrate_rectification")

    def benchmarks():
        run("feasibility/scripts/evaluate.py")
        run("feasibility/scripts/build_report.py")
        for name in ("evaluate_stone_accuracy", "evaluate_body_localization", "run_vision"):
            proto(name)
        proto("evaluate_vision")
        proto("evaluate_vision", "--include-check")
        proto("build_vision_viewer")
        proto("audit_rectification")
        proto("check_body_transfer")

    def continuous():
        proto("process_continuous")
        proto("audit_continuous")
        proto("render_rectification")
        proto("process_body_video")

    def throws():
        proto("detect_throws")
        proto("evaluate_throws")
        proto("audit_pre_gate")
        # Both cameras read the newly generated events; neither consumes the other.
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as cameras:
            camera_futures = [
                cameras.submit(proto, name)
                for name in ("process_throw_segments", "process_departure_geometry")
            ]
            for future in camera_futures:
                future.result()
        proto("build_throw_segments")
        proto("review_segment_endpoints")
        proto("build_cross_view")
        proto("render_cross_view_evidence")
        proto("render_pre_gate_evidence")

    # These branches write disjoint outputs and share only immutable inputs.
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(fn) for fn in (benchmarks, continuous, throws)]
        failures = []
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as error:
                failures.append(str(error))
        if failures:
            report["failures"] = failures
            save()
            raise RuntimeError("; ".join(failures))
    proto("analyse_throw_target")
    proto("audit_trajectory")
    proto("build_trajectory_evidence")
    proto("build_throw_viewer")
    run("research/meeting/build_briefing.py")
    for relative, (original, original_sha) in baseline.items():
        p = work / relative
        delta = differences(original, load(p)) if p.exists() else ["Output missing"]
        report["comparisons"].append(
            {
                "file": relative,
                "passed": not delta,
                "original_sha256": original_sha,
                "fresh_sha256": sha(p) if p.exists() else None,
                "differences": delta,
            }
        )
    save()
    run("scripts/validate.py", "--artifacts", "--browser")
    report["execution_passed"] = all(s["returncode"] == 0 for s in report["steps"])
    report["strict_comparison_passed"] = all(c["passed"] for c in report["comparisons"])
    report["passed"] = report["execution_passed"] and report["strict_comparison_passed"]
    save()
    print("RESULT", report_dir / "report.json", "passed", report["passed"], flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
