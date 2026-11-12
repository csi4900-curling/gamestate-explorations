# Curling trajectory reconstruction

Build **one reliable pipeline for left/right split-screen curling broadcasts**,
with accurate trajectories and consistent stone identity across observations,
camera views, occlusions and trajectory fragments. New recordings must not need
manual calibration or per-video rule tuning. Other broadcast formats and broad
transfer-learning evaluation are deferred.

**This goal is not yet achieved.** The current public runner is a development
integration with incomplete tracking and provisional identity. The discarded
receiving passes were removed in a labelled development change, with exact
final-output equivalence on a 45-second clip; full-match regression is pending.

> **25 October 2026 — full-match Canada–Sweden development run in progress.**
> The frozen observation run is processing the full match. CoTracker/dense was
> removed from this deliverable by owner decision after a value review; the
> final report, synchronized viewer and delivery checklist will therefore cover
> the observation/aggregate pipeline and will state that the all-events dense
> requirement was not met. Outputs go to
> `validation/full-match-development-2026-10-23/final/`.
> Live status and evidence boundary:
> [STATUS](validation/full-match-development-2026-10-23/STATUS-2026-10-25.md).
> Process/cost analysis:
> [PROCESS_OPTIONS](validation/full-match-development-2026-10-23/PROCESS_OPTIONS-2026-10-25.md).
> Final report addendum:
> [FINAL_REPORT_ADDENDUM](validation/full-match-development-2026-10-23/FINAL_REPORT_ADDENDUM.md).
> A durable user service carries the run across service loss and reboots. The
> 22 October material below remains historical context.

## Start here

- [Latest development deliverable: dense tracking, synchronized projection and spin results](validation/spin-development-2026-10-22/index.html)
- [What this deliverable implements and how to run it (French)](docs/SPIN_DELIVERABLE.md)
- [Exact current pipeline, stage order and limitations](docs/CURRENT_PIPELINE.md)
- [Standing scope and evidence requirements](AGENTS.md)
- [Required product outputs and acceptance contract](docs/LEFT_RIGHT_REQUIREMENTS.md)
- [Established-model shortlist and spin methodology](docs/MODEL_SELECTION.md)
- [Original integrated output viewer](validation/meeting-2026-10-22/runtime/index.html)
- [Diagnostic viewer bypassing the departure ring gate](validation/meeting-2026-10-22/runtime-no-ring/index.html)
- [French supervisor report](supervisor-progress-2026-10-22.pdf)
- [Archived original-workflow comparison](validation/meeting-2026-10-22/archived-comparison/control-regression.json)

The diagnostic viewer is a postprocessing experiment; it is **not** the default
pipeline and is not evidence of improved accuracy. Both viewers default to both
camera tracks. Source observations, projections and cross-camera associations
remain distinct and may be wrong.

The new optional `--track-candidate SEGMENT_ID` stage uses the upstream CoTracker3
implementation, seeded from an existing split-camera observation. It adds dense
image tracking and a conditional camera-local projection using an existing
calibration plus the existing camera-registration routine. It does not replace
the baseline aggregate or establish physical trajectory accuracy. No new rink
calibration is fitted by this added stage; the baseline still has its prior
calibration behavior. Handle tracking has not yet yielded reliable physical spin.

## Current executable entry point

```bash
feasibility/scripts/python.sh prototype/scripts/run_throw_pipeline.py \
  --video /absolute/path/to/video.mp4 --source-id RECORDING_ID \
  --start 0 --end END_SECONDS --layout-chunk-s 90 --allow-partial \
  --output-dir /absolute/path/to/new-output --audit-source-activity
```

Replace the placeholders; use a new output directory. This invokes the existing
implementation described in the pipeline document. It does not invoke the
archived original workflow or the no-ring diagnostic. It still contains a legacy
Beijing adapter; cleanup has not changed inference or removed that code branch.

## Repository map

| Location | Role |
| --- | --- |
| `prototype/` | Current algorithms, executable scripts and tests; includes historical experiments. |
| `validation/` | Recordings, models, annotations, frozen runs and evaluation evidence. Preserve provenance. |
| `feasibility/` | Runtime wrapper/environment and earlier feasibility work. |
| `research/` | Literature, footage investigations and report builders. |
| `docs/` | Current pipeline inventory, cleanup ledger and archived documentation. |

## History and cleanup

The previous long README mixed experiments, old completion claims and launch
instructions. It is preserved as [historical documentation](docs/history/README-before-scope-cleanup-2026-10-22.md),
not current guidance. Recordings, models and previous results remain in place.
211 recording-specific leaf scripts were archived after checking source references.
Historical commands for those scripts require restoration from the archive.
The [script cleanup manifest](docs/cleanup-scripts-2026-10-22.json) records exact
paths, hashes and the recovery command. Runtime dependencies were retained.

[Cleanup ledger](docs/cleanup-2026-10-22.json): obsolete report copies and the
removed tracking-status UI were archived; disposable tool/Python caches removed.
Source data, models, labels, failures and measured results were not deleted.
