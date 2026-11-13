# Research, evidence and history

For new analyses, use the [app-workbench](WORKBENCH.md). Research scripts and
historical runners support investigation and baseline reproduction; their
presence does not make them part of the app execution path.

| Location | Contents |
| --- | --- |
| `prototype/` | Application modules alongside component experiments, scripts and tests. Use the workbench execution guide to identify active stages. |
| `validation/` | Local recordings, annotations, frozen/development runs, failures and review evidence. Many assets are absent from Git. |
| `research/` | Literature, footage investigations, model probes and report builders. |
| `feasibility/` | Runtime wrapper and earlier feasibility experiments. |
| `docs/history/` | Earlier README versions, preserved as historical records. |
| `docs/archive/` | Earlier cleanup archives. |

## Current references

- [Product acceptance contract](LEFT_RIGHT_REQUIREMENTS.md)
- [Standing evidence and preservation requirements](../AGENTS.md)
- [Source-only labelling tool](../prototype/source_label_tool.html): labels from
  source video, separate from model predictions. Its JSON flag is not proof of
  reviewer independence; record actual review conditions. By-eye turns are not
  independent metric trajectory measurements.
- [Revolution-period research probe](../research/revolutions-2026-11-12/README.md):
  development research outside the app pipeline, with no validated physical count.

## Historical material

- [Previous project README](history/README-before-workbench-navigation-2026-11-12.md):
  preserved verbatim with operating history, scoring caveats, import examples,
  research commands and evidence references. Its relative links were written for
  the repository root; resolve them from there.
- [Earlier pipeline audit and dated updates](CURRENT_PIPELINE.md): historical
  inventory, not the current app execution guide.
- [Prototype milestones](../prototype/README.md): earlier indexer and experiments.
- [Model shortlist and spin methodology](MODEL_SELECTION.md)
- [Historical spin deliverable](SPIN_DELIVERABLE.md)
- [October script cleanup manifest](cleanup-scripts-2026-10-22.json) and
  [cleanup ledger](cleanup-2026-10-22.json): archived paths, hashes and recovery.

Historical results retain their original evidence limits. A preserved viewer,
source-point score or calibration fit does not establish complete-trajectory
accuracy or generalization. Frozen runs, unfavorable results and development
outputs must keep their provenance when reused.

This navigation cleanup moves no source modules, models, recordings or run
outputs. It changes no inference, thresholds, association or calibration rules.
