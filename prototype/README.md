# `prototype/` — Active Left/Right Curling Pipeline Package

This package contains the active 39-module left/right split-screen curling
analytics pipeline and local web workbench. Earlier exploratory scripts and
experiment dumps were pruned from this tree and remain preserved in git history
(through commit `1e6c5e8`).

## Launch the Workbench

From the project root:

```sh
./curling-workbench
```

Open **http://127.0.0.1:8766**.

## Run the Test Suite

```sh
PYTHONPATH="$PWD" feasibility/scripts/python.sh -m pytest -q prototype/tests
```

## Documentation

- [Workbench Operating Guide](../docs/WORKBENCH.md) — starting, calibrating,
  running, rebuilding, and reviewing matches.
- [Current Pipeline Architecture & 39-Module Code Map](../docs/CURRENT_PIPELINE.md)
  — end-to-end data flow and guided reading order for every module in this
  package.
- [Acceptance Contract & Scope](../docs/LEFT_RIGHT_REQUIREMENTS.md) — project
  requirements, explicit calibration policy, and evidence boundaries.
