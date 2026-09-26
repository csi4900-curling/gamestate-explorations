# Full vision reproduction, 25 September 2026

**The reported outcomes reproduced in a fresh Python environment. The raw numbers are not identical at every decimal place.** All 94 software tests and seven browser checks passed on the rebuilt outputs.

## What was rerun

A new Python 3.13 virtual environment was installed without system site packages on the same Linux host. Its package versions are recorded in `installed.txt` and the root `requirements-lock.txt`. System FFmpeg, Chromium and native runtime libraries were reused; this was not a fresh operating system installation.

The project was copied to an isolated workspace. All 59 measured output files, including every receiving/departure observation cache, were removed there before processing. Original project results were preserved.

The run rebuilt:

- Manual-calibration evaluation and both selected-frame stone benchmarks.
- Snapshot detection evaluation, ring refinement and calibration checks.
- The full 18.5-minute interval for throw detection, all 16 receiving windows and all 16 departure tracks.
- The continuous 90-second experiment, including projection of all 2,700 video frames and stone observations sampled at 2 Hz.
- Pre-gate measurements, segment summaries, cross-view associations, aiming-reference and trajectory comparisons, evidence images and HTML reports.

This uses the saved media, review/reference images, manual annotations, diagram-coordinate CSV and frozen protocols as inputs. It does not repeat manual labelling, re-download media, reconstruct historical abandoned runs, or reproduce external publications/simulator tests. The advanced native-resolution processing still covers selected windows, not every frame of the full match.

## Results

| Check | Reproduced result |
|---|---|
| Baseline stone detector | 4/48 detected |
| Replacement detector | 46/48 detected; 40/48 within 10 cm of diagram references |
| Throw passages | Same 16 events, event times and pixel tracks |
| Cross-view links | Same 16 provisional links; 499 positions from 513 departure samples |
| Projection availability | Left: 2,700 accepted; right: 2,688 accepted, 12 unavailable |
| Moving trajectory labels | Pixel RMSE unchanged: 1.1590621208546035 px |
| Conditional trajectory discrepancy | 3.9036630536 cm before; 3.9036629621 cm after |
| Discrete output changes | None across the 59 compared files: no changed IDs, counts, statuses or list lengths |
| Largest compared stone-position shift | 0.000342698 mm |
| Largest compared pixel-vector shift | Below 0.000000000002 px |

The initially declared strict numeric tolerance was `1e-9` absolute/relative. **19 files passed that comparison and 40 failed it** because of numerical differences, principally after refitting calibration. The tolerance was not increased to turn the run green. `report.json` therefore retains `passed: false` and `strict_comparison_passed: false`, alongside `execution_passed: true`. Every processing command and the final software/browser validation succeeded.

`drift.json` measures the differences across all output values. Matrix coefficients, camera parameters and ring-quality scores have different units from stone positions; their changes must not be described as position errors. A repeated clean calibration fit produced identical matrices to the first clean fit. The largest change from the archived calibration at the annotated rink points was about 0.000034 mm.

**Repeatability does not establish physical accuracy.** Diagram references, manual pixel estimates, assumed camera parameters and provisional identities retain their original limitations.

## Corrections exposed by the clean run

- The stored pre-gate consistency check used exact floating-point equality and failed on differences below `5e-16` pixels. It now uses the same declared `1e-9` comparison tolerance while preserving structural checks.
- A browser seek check relied on a fixed half-second delay. It now waits for seek completion and the expected displayed sample; the playback check also waits for actual video progress.

Inference kernels and manual labels were not changed to obtain matching results. The initial failed check logs are retained.

## Evidence and repeat command

- `summary.json`: concise findings.
- `report.json`: commands, timings, input fingerprints, original/fresh output hashes and strict differences.
- `drift.json`: numerical magnitudes and discrete-change checks for every output file.
- `environment.json`, `installed.txt`, `ffmpeg.txt`, `code-sha256.json`: execution provenance.
- `calibration-repeat.json`: second clean-fit comparison.
- `fresh-output-validation/report.json`: passing validation on the freshly generated results, with individual logs alongside it.

Departure processing ran concurrently in the isolated workspace; `process_departure_geometry-fresh.txt` records all 16 fresh computations. The driver's subsequent departure call validated those newly generated caches. Endpoint evidence was also regenerated in a supplemental successful command. These runs are recorded explicitly in `report.json`; no archived per-throw cache was reused. The current runner schedules both camera processors concurrently itself.

Follow the root README's **Full isolated reproduction** commands. Original baseline results are required for comparison. Future runs can show different last digits across numerical builds; inspect the differences instead of silently overwriting the baseline or modifying reference checksums.
