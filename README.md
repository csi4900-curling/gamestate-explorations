# Curling app-workbench

The **app-workbench is the core application** for running new analyses of
left/right split-screen curling broadcasts. It loads recordings, records operator
calibration and analysis settings, runs the shared pipeline, and opens synchronized
throw, trajectory and stone-observation views.

```sh
./curling-workbench
```

Open **http://127.0.0.1:8766**. This command uses the configured local environments
and models; a fresh clone alone is insufficient. See the
[workbench guide](docs/WORKBENCH.md) for dependencies, analysis steps, recovery
and the code execution path.

## Run an analysis

1. Load a local recording or upload a video and select its analysis interval.
2. Open **Camera calibration**, mark source rink features for both panels, reserve
   check points, inspect the projection and confirm the operator record. Select
   source-bound calibration records covering the requested interval.
3. Set the event crossing line, team colours and physical settings in the form.
4. Start the analysis and inspect stage progress and logs.
5. Review **Throws**, **Trajectories** and **Stone observations**, including
   unresolved candidates and gaps. Save candidate reviews separately from predictions.

Runs and reviews persist under `workbench-data/`. Failed and interrupted runs are
preserved; supported reuse and rebuild actions create separate runs.

## Current development results

On the 14-minute Norway–Czechia (NOR–CZE) development interval, the app detected
10 throws. **All 10 have trajectory observations.** A trajectory shows the
observed stone path; a **throw result** compares the board before and after the
throw, including which stones moved and the proposed points lying afterwards.

| Output | Available for the detected throws |
| --- | --- |
| Trajectory observations | **10 of 10**; observations can contain gaps and provisional camera associations. |
| Throw-result proposals | **9 of 10** in the later saved development rebuilds. |

The unresolved **throw result** is throw 2 (`L00002`, crossing at approximately
3:04). It has two receiving-track candidates, so the result stage cannot select
a single receiving track unambiguously. Its trajectory observations remain
available.

Earlier outputs had **8 of 10 throw-result proposals**. They also lacked a result
for throw 4 (`L00004`, crossing at approximately 6:46), because its receiving
track had no observed moving-to-stationary transition. Later development
rebuilds (`cc2bd6112d28`, `dcc67f9d443f`) reused the same observation stream and
produced a board-level quiet-window proposal for throw 4, bringing the count to
9 of 10. The earlier failures remain preserved. This change concerns throw-result
postprocessing, not the number of throws with trajectory observations.

These counts describe available outputs, not verified accuracy. They cover the
10 detected throws; missed throws have not been counted. Three throws in the
earlier output were compared with source frames by the developing agent while
predictions were visible. That review is not independent ground truth and does
not verify the later rebuild's proposals.

## What still needs verification

The [playbook delivery map](docs/PLAYBOOK_DELIVERY.md) connects all 18 original steps to their evidence requirements and the latest same-input workbench regression.

The application runs a **development pipeline**. We have not yet established:

- **Reliability on unseen matches:** the same frozen pipeline must be evaluated
  on recordings that were not used to develop it. Norway–Sweden remains reserved
  for that evaluation.
- **Physical stone identity:** tracker IDs and camera links do not yet prove that
  the same physical stone is followed through occlusions, collisions and both views.
- **Absolute position accuracy and trajectory completeness:** operator calibration
  checks and cross-camera agreement do not independently measure physical error
  or establish full observable-path coverage. Positions depend on calibration.
- **Physical revolution counts:** these remain unvalidated.

The [acceptance contract](docs/LEFT_RIGHT_REQUIREMENTS.md) defines the required
outputs and evaluation. The provisional position targets are **10 cm median
error** (half of measured errors at or below 10 cm) and **25 cm p95 error**
(95% at or below 25 cm). These are targets, not measured performance. The
[standing instructions](AGENTS.md) govern evidence and baseline preservation.

## Find your way around

| Location | Role |
| --- | --- |
| [Workbench guide](docs/WORKBENCH.md) | Current operation, execution stages, configuration, outputs and checks. |
| `curling-workbench` | Public application launcher. |
| `prototype/workbench.py`, `prototype/workbench.html` | Application server, job orchestration and UI. |
| `prototype/product_pipeline.py` | Shared trajectory, board and result assembly invoked by the app. |
| `prototype/config/workbench.json` | Default runtime and pipeline profile. |
| `prototype/tests/` | Behavioral and component tests, including historical experiments. |
| `workbench-data/` | Local recordings registry, calibrations, jobs and reviews; outside Git. |
| [Research and history guide](docs/RESEARCH_AND_HISTORY.md) | Experiments, preserved evidence and earlier runners. |

Runtime modules and historical experiments currently share `prototype/`.
The workbench guide identifies the active execution path; directory membership
alone does not mean an experiment runs in the app. Models, source recordings and
most run evidence are local assets outside the committed repository.
