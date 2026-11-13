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

## Current evidence boundary

The application runs a **development pipeline**. Reliable end-to-end trajectory
generalization, physical stone identity and absolute metric accuracy have not
been established. Operator calibration checks and cross-camera agreement do not
establish physical accuracy. Tracker IDs remain provisional physical identities.

The Throws view was checked on one 14-minute NOR–CZE development interval:
8 of 10 detected throws received a board and 2 stayed unresolved. Three throws
were compared with source frames by the developing agent with predictions visible;
this is not independent ground truth. Missed throws are outside those counts.
Positions inherit unverified calibration. Physical revolution counts remain
unvalidated. Norway–Sweden remains reserved for frozen evaluation.

The [acceptance contract](docs/LEFT_RIGHT_REQUIREMENTS.md) defines the required
outputs and evaluation. The provisional position targets are 10 cm median and
25 cm p95 error; these are targets, not measured performance. The
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
