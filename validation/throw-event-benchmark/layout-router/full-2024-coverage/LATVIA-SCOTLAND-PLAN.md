# Latvia and Scotland full-source transfer plan

This plan precedes the full-source layout preflights and event passes below.
Both sources have exposed 1650–2760 s development intervals, so this is a
same-production coverage transfer, not an untouched event-accuracy test.

Run the existing `prototype/scripts/run_throw_pipeline.py` unchanged on the
locally cached 360p Canada–Latvia and Canada–Scotland 2024 full recordings.
Use `[0, 7059]` and `[0, 7347]` seconds respectively and the existing
90-second layout chunks. Retain unknown chunks as gaps with `--allow-partial`.
Do not adjust the router or span/context thresholds after inspecting either
output. Preserve every raw proposal in `triage.json` and report candidate
counts separately from confirmed physical throws.

Before any full-source run, inspect each preflight's supported time and
unknown gaps. Following the runs, compare the earlier fixed interval only
as a reproducibility check; earlier interval outcomes are development data.
The results cannot establish physical-event precision, recall or F1 without
an exhaustive independent timestamped reference, and they cannot establish
game-state or simulation readiness.
