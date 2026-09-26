# Curling video research prototype

A source-specific experiment for converting curling video into timestamped stone observations, throw passages, partial trajectories and provisional links between two camera views.

**Start here:** `supervisor-briefing.html` explains the experiments; `prototype/cross-view/index.html` is the latest two-view demo. These local viewers need their surrounding data and video files. The generic upload page is an older image indexer and does not run the advanced pipeline.

## Set up

Recorded environment: Linux, Python 3.13. Native video preparation also uses `ffmpeg` on PATH.

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m playwright install chromium
```

On Windows, use `.venv\Scripts\python.exe`. On ordinary Linux/macOS, `.venv/bin/python` works directly. The `feasibility/scripts/python.sh` wrapper supplies library paths required by this project's Nix host. `CURLING_PYTHON` can select another Python executable. A fresh Linux/Python 3.13 installation succeeded without system site packages. `requirements-lock.txt` records its direct and transitive package versions; use it instead of `requirements-dev.txt` to recreate that complete package set. Other operating systems have not been tested.

## Validate

```sh
feasibility/scripts/python.sh scripts/validate.py
# With the recorded experiment data present:
feasibility/scripts/python.sh scripts/validate.py --artifacts
# With source videos and Playwright also present:
feasibility/scripts/python.sh scripts/validate.py --artifacts --browser
```

The runner checks syntax, unit/integration tests, dependency consistency, lint and formatting. Optional checks recompute stored metrics and launch a temporary loopback server for browser tests. It writes `validation/report.json` and individual logs. `CHROMIUM_EXECUTABLE` overrides browser discovery; `CURLING_BROWSER_PYTHON` selects a separate Playwright environment if needed.

See [the audit](validation/AUDIT.md) for what was checked and remaining limitations. Software tests do not establish real-world vision accuracy.

## Implementation map

| Component | Code | Responsibility |
|---|---|---|
| Calibration and registration | `prototype/vision_core.py`, `prototype/rectification_core.py` | Pixel-to-ice homographies, ring refinement, SIFT/LK registration |
| Stone observations | `prototype/body_localization.py` | Classical colour/body detection and conditional height correction |
| Local tracking | `prototype/continuous_tracker.py` | Simple same-colour image-space association; camera-local IDs |
| Throw events | `prototype/throw_detection.py` | Outgoing virtual-line crossings, not exact release instants |
| Segment boundaries | `prototype/throw_segmentation.py` | Passage-to-next-passage review intervals and visible-stability candidates |
| Cross-view linkage | `prototype/cross_view.py` | Explicit coordinate transforms and unique receiving hog-line association |
| Evaluation | `prototype/stone_accuracy.py`, `prototype/pre_gate_geometry.py` | Detection matching, position discrepancies and straight-line residuals |
| Intent | `prototype/shot_intent.py` | Refuses to treat an aiming broom as a confirmed resting destination |
| Experiment scripts | `prototype/scripts/` | Source-specific processing, reports and browser checks |
| Historical upload indexer | `prototype/pipeline.py`, `prototype/server.py` | Coarse thumbnails and local upload/review |

Core detector versions and several historical geometry helpers remain byte-for-byte frozen so recorded fingerprints can still be verified. New orchestration, validation and handoff code is formatted. Standalone experiment scripts intentionally execute when run; import the core modules, not the scripts, from other code.

## Reproduce the latest experiment

This experiment uses the Canada–Korea composite recording, source interval 1650–2760 seconds. Source details and hashes are in `prototype/throw-analysis/source.json`; per-view landmarks are in `prototype/vision/annotations/calibration.json`. Source videos are separate from the code handoff.

1. `detect_throws.py` produces departure events from the full 360p recording.
2. `process_throw_segments.py` processes receiving windows from the 1080p end clip.
3. `process_departure_geometry.py` re-detects the saved departure observations at 1080p.
4. `build_throw_segments.py` and `build_cross_view.py` derive the review artifacts.
5. `render_cross_view_evidence.py` creates image comparisons.

Each command uses `feasibility/scripts/python.sh prototype/scripts/NAME.py`. The two processing scripts now validate cache fingerprints. Archived outputs from before that contract are **not silently reused**: use `--output /path/to/new/results --limit 1` for an isolated smoke run, or back up the experiment directory and use `--force` for a complete recomputation in its standard location. Report builders use the standard locations. Re-run `research/meeting/build_briefing.py` after updating results to embed demo data for offline viewing.

For the selected-frame benchmark, run `evaluate_stone_accuracy.py` then `evaluate_body_localization.py`. They verify the frozen benchmark inputs before inference. Do not overwrite the annotation protocol to make a failed check pass.

### Full isolated reproduction

The completed clean run reproduced the reported outcomes across 59 output files, with tiny numerical differences and no changed discrete decisions. All 94 tests and seven browser checks passed on its regenerated outputs. See [the full reproduction audit](validation/full-reproduction/README.md) for scope, differences and evidence.

With the saved project inputs present, use a **new environment** and a **nonexistent workspace directory outside this repository**:

```sh
python3.13 -m venv /tmp/curling-clean-env
/tmp/curling-clean-env/bin/python -m pip install -r requirements-lock.txt
# If Chromium is not already installed:
/tmp/curling-clean-env/bin/python -m playwright install chromium
CURLING_PYTHON=/tmp/curling-clean-env/bin/python feasibility/scripts/python.sh \
  scripts/reproduce.py --workdir /tmp/curling-clean-run
```

The runner copies the project, deletes the measured output files and both camera caches in that copy, rebuilds the experiments, compares detailed results with the original files, and runs the software/browser checks. It processes the full 18.5-minute interval for throw detection, each throw's receiving/departure windows, and all 2,700 frames of the 90-second projection clip. It does not infer every native-resolution frame of the full match.

Required inputs include exact video files, saved review/reference images, manual annotations, the diagram-coordinate CSV and frozen benchmark protocols. The recorded baseline outputs must also be present for comparison; the runner refuses to claim reproduction without them. These are experiment inputs, not automatically regenerated labels. Re-downloading a URL is not guaranteed to produce identical video bytes. The run records input hashes and package versions in `validation/full-reproduction/` and preserves the original project outputs.

Comparisons exclude explicitly listed runtime/cache provenance fields. Numerical comparison uses absolute and relative tolerances of `1e-9`; tiny fitting differences can therefore fail the strict comparison even when reported measurements agree. Such differences remain visible rather than silently increasing the tolerance. To inspect their magnitudes:

```sh
python scripts/describe_reproduction_drift.py /tmp/curling-clean-run \
  --output validation/full-reproduction/drift.json
```

## What the results establish

- 46/48 stones detected and 40/48 within 10 cm of diagram references on selected development frames.
- 16 departure passages found in one annotated end.
- 16 provisional two-view links on that same end, with explicit gaps.
- Camera intrinsics, feature height, rink orientation and panel timing still involve assumptions.
- The release point, full pre-release delivery, physical trajectory accuracy, complete throw endings and generalization to unseen videos remain unvalidated.

The latest cross-view rule was developed after inspecting this end, including T08. Its 16 proposed links are **not 100% independently measured identity accuracy**. Older READMEs and run logs document earlier milestones; the root report and audit identify the current scope.

## Sharing

`python scripts/package_code.py` creates `dist/curling-code.zip`: source, documentation and the small fixtures needed for unit tests. It excludes the Python environment, downloaded recordings, raw download metadata and generated experiment results. To run the demos or reproduce the original experiments, provide the separate project data folders as well. No project-wide license has been selected; third-party data/software retain their own terms.
