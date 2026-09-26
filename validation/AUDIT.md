# Code audit and partner handoff

## Scope and conclusion

The source in this workspace has been reviewed for algorithm/data flow, evaluation claims, input handling, reproducibility, portability and browser behavior. The project is ready for a **research-code review by the team**, with the experimental limits below made explicit. This is not a certification of customer-ready vision accuracy.

The audit covers the prototype, feasibility helpers, research/report scripts, tests and local viewers. It does not re-audit the external simulators or reproduce published neural-model results. Source-specific experiment scripts remain separate from reusable core modules.

## Corrections made

| Finding | Change |
|---|---|
| Existing JSON could be silently reused after calibration, model, video or parameters changed | Receiving/departure processing now fingerprints inputs, reference images, implementation, library versions and event ID. Mismatched or unversioned caches are rejected; explicit `--force` or an empty `--output` is required. Writes are atomic. |
| Invalid coordinates/times could reach association or stability logic | Added finite/shape checks, strictly increasing times, matching event IDs, segment-boundary enforcement, and rejection of invalid or duplicate visible observations. |
| A trajectory audit regenerated its own manual reference and checksum | It now reads the existing reference and verifies its checksum without overwriting annotations. |
| Browser scripts required a machine-specific Chromium path | Browser executable discovery and explicit environment overrides replace the fixed path. The validation runner starts/stops its own isolated local server. |
| A fixed-delay browser assertion raced video seeking | It waits for the actual seek completion and unavailable-geometry display. |
| HTTP unsatisfiable ranges lacked the required size metadata | Responses now include `Content-Range: bytes */size`; full/suffix/invalid ranges and upload validation have regression tests. |
| Setup instructions and “latest” README content were stale | Added root setup, architecture map, validation commands, source/data requirements and an explicit distinction between the historical upload indexer and advanced experiments. |
| Compact orchestration scripts were difficult to read | Formatted non-frozen Python code and removed unused imports. Frozen experimental cores retain their recorded bytes. |
| The historical continuous viewer still fetched JSON when opened from disk | Its JSON is now embedded by the same offline-data build step as the other reports. |

## Checks and evidence

- **Follow-up full reproduction:** [full-reproduction/README.md](full-reproduction/README.md). All current vision experiments were rebuilt in a fresh Python environment and an isolated workspace with original inference caches removed. All reported outcomes and discrete decisions reproduced; small numerical differences remain explicitly recorded. All 94 tests and seven browser checks passed on the rebuilt outputs.
- `report.json`: reproducible validation-run status and links to individual logs.
- `unit.txt`: 90 prototype unit and integration tests, including an actual synthetic-video indexing run and a temporary HTTP server.
- `geometry.txt`: 4 original feasibility geometry tests.
- `artifacts.txt`: frozen input/model hashes, recomputed 48-target position errors, all stored cross-view decisions and pre-gate straight-line calculations.
- `stone-reproduction.txt`, `body-reproduction.txt`: fresh inference on the selected-frame benchmark. Both headline summaries were reproduced exactly, including 4/48 baseline detections, 46/48 replacement detections and 40/48 within 10 cm.
- `receiving-smoke.txt`, `departure-smoke.txt`: fresh native-video processing for T01 in isolated output folders. These are new computations, not reads of the existing experiment outputs. Both fresh observation sequences matched the recorded T01 observations exactly; see `reproduction.json`.
- Browser checks: static benchmark, rectification, body localization, throw events, segment review, cross-view linkage and supervisor report; playback, seeking, controls, links and mobile layout are checked where applicable.
- The code-only ZIP is also tested after extraction using the existing Python environment. This checks the bundle contents, not a clean dependency install on another OS.

## What remains limited

1. **Data and camera specificity.** The current experiments use fixed layouts, manual landmarks and source-specific thresholds. The upload endpoint still only indexes frames.
2. **Physical accuracy.** Diagram agreement, same-image landmark residuals and detector/manual pixel agreement are different quantities. None is an independently surveyed full-trajectory accuracy measurement.
3. **Cross-view identity.** Sixteen links are proposed on the same end used to develop the rule. Rink orientation, panel timing and feature height retain explicit assumptions. The middle gap is not reconstructed.
4. **Tracking and endings.** Greedy local associations can switch identity under occlusion or collision. Visible stability does not prove that hidden or undetected stones have stopped. Display truncation does not repair a wrong track.
5. **Model boundary.** Frozen CV kernels expect the documented calibrated source inputs. They are not general-purpose hardened APIs for arbitrary matrices or malformed external data. The new orchestration checks its supported inputs.
6. **Reproduction coverage.** The follow-up reran full-interval throw detection, all 16 camera windows/tracks, the complete 90-second projection clip and the current evaluations from saved input data. Numerical outputs are not identical at every decimal place. The recorded source media, review images, manual labels and protocols remain required inputs; external research results and historical abandoned runs were not reproduced.
7. **Portability.** A fresh isolated Python 3.13 installation and full validation succeeded on the same Linux host. Clean installation on Windows/macOS, a fresh OS or every supported Python version has not been established.
8. **Maintenance.** Several experiment builders still contain large HTML templates. They are reproducible standalone scripts, not a packaged service or production application. There is no automatic trained model, deployment pipeline or complete simulator export.

## Suggested team review

Start with `cross_view.py`, then `body_localization.py` and the calibration conventions. One teammate should independently label release/arrival identities and endings; another should reproduce the recorded checks in a clean environment. Preserve an unseen recording for evaluation before further tuning.
