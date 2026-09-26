"""Portable validation entry point. Optional browser checks use a temporary local server."""

from pathlib import Path
import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--browser", action="store_true", help="Run media/browser checks; needs videos and Playwright"
)
parser.add_argument(
    "--artifacts", action="store_true", help="Recompute metrics from stored experiment artifacts"
)
args = parser.parse_args()
out = ROOT / "validation"
out.mkdir(exist_ok=True)
results = []


def run(name, cmd, env=None):
    print(name, flush=True)
    with (out / (name + ".txt")).open("w") as log:
        try:
            r = subprocess.run(
                cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180
            )
        except subprocess.TimeoutExpired:
            log.write("Validation command exceeded 180 seconds.\n")
            r = subprocess.CompletedProcess(cmd, 124)
    results.append(
        {
            "check": name,
            "passed": r.returncode == 0,
            "log": str((out / (name + ".txt")).relative_to(ROOT)),
        }
    )
    if r.returncode:
        print((out / (name + ".txt")).read_text()[-3500:], flush=True)


run(
    "compile",
    [
        sys.executable,
        "-m",
        "compileall",
        "-q",
        "prototype",
        "feasibility/scripts",
        "research/meeting",
        "research/footage-audit/scripts",
        "scripts",
    ],
)
run("unit", [sys.executable, "-m", "unittest", "discover", "-s", "prototype/tests", "-v"])
run(
    "geometry",
    [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        "feasibility/scripts",
        "-p",
        "test_*.py",
        "-v",
    ],
)
run("dependencies", [sys.executable, "-m", "pip", "check"])
ruff = shutil.which("ruff") or str(Path(sys.executable).parent / "ruff")
if not Path(ruff).exists():
    raise SystemExit("Install requirements-dev.txt: ruff is required.")
run(
    "lint",
    [
        ruff,
        "check",
        "prototype",
        "feasibility/scripts",
        "research/meeting",
        "research/footage-audit/scripts",
        "scripts",
    ],
)
run(
    "format",
    [
        ruff,
        "format",
        "--check",
        "prototype",
        "feasibility/scripts",
        "research/meeting",
        "research/footage-audit/scripts",
        "scripts",
    ],
)
if args.artifacts:
    run("artifacts", [sys.executable, "scripts/check_artifacts.py"])
if args.browser:
    browser_python = os.environ.get("CURLING_BROWSER_PYTHON", sys.executable)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = dict(os.environ, CURLING_BASE_URL=f"http://127.0.0.1:{port}")
    with (out / "server.txt").open("w") as log:
        proc = subprocess.Popen(
            [sys.executable, "prototype/server.py", "--port", str(port)],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            for _ in range(100):
                if proc.poll() is not None:
                    raise RuntimeError("Validation server exited")
                try:
                    with urllib.request.urlopen(env["CURLING_BASE_URL"], timeout=0.5):
                        break
                except OSError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Validation server did not start")
            for name in [
                "check_stone_accuracy_browser",
                "check_rectification_browser",
                "check_body_browser",
                "check_throw_browser",
                "check_throw_segments",
                "check_cross_view",
            ]:
                run(name, [browser_python, "prototype/scripts/" + name + ".py"], env)
            run("briefing", [browser_python, "research/meeting/check_briefing.py"], env)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
report = {
    "python": sys.version,
    "checks": results,
    "passed": all(r["passed"] for r in results),
    "scope": "Software checks and consistency of recorded experiments; no independent real-world CV accuracy certification.",
}
(out / "report.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
sys.exit(0 if report["passed"] else 1)
