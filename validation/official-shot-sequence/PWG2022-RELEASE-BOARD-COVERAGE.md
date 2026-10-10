# Release-cue overlap with video-derived partial boards

The [reproducible broad-window join](pwg2022-release-to-board-handoff-development.json) connects the latest nine video-derived partial board observations to the provisional event union by their shared delayed counter, then looks up the first within-view release-cue scan. The [held-shot correction](pwg2022-held-shot-release-to-board-development.json) rescans the two China travel-only events with attached origin shots inside those shot boundaries and repeats the join. Both artifacts preserve source hashes, event IDs, board intervals, cue status, and explicit false flags for delivered-stone identity, physical transition, and simulation readiness.

| Recording | Partial boards | Unique counter-linked provisional event | Board-linked event with one within-view release cue |
| --- | ---: | ---: | ---: |
| Switzerland | 5 | 5 | 0 |
| China | 3 | 3 | 1 after held-shot rescan |
| Slovakia | 1 | 1 | 0 |
| **Total** | **9** | **9** | **1 after held-shot rescan** |

The original broad-window join has **0/9** unique passages. That is a reproducible result of its scan scope, but it missed a usable cue in China B57: the broad delivery window spans several camera shots and contains two red passages, so the scanner abstains. The [held-shot rescan](pwg2022-held-shot-release-to-board-development.json) restricts B57 to its attached origin shot S278 (3452.2–3464.0 s) and finds one red held-to-motion passage at **3459.8 s**. The other attached-held travel event, B56, also has one cue in its own shot; it has no linked partial board. Thus **1/9** boards now has a provisional within-view cue. The headline **111/356** still describes the original unchanged broad-window transfer, not this scoped correction.

This count is cue coverage on nine selected *candidate* windows, not physical throw recall. The B57 cue, receiving-view travel and later partial board form a timed evidence chain through a delayed counter. They do not establish that the same physical stone persisted across views or produced the observed board. Broadcast edits may hide release, the cue can abstain, and counter links can be wrong. Every board remains partial, unitless and uncalibrated for simulation. A full event-to-state reconstruction still needs delivered-stone identity through the receiving view and a verified settled-board transition.

Run `python prototype/scripts/audit_pwg2022_release_board_handoff.py` to reproduce the historical broad-window join. Run `PYTHONPATH=. feasibility/scripts/python.sh prototype/scripts/audit_pwg2022_held_shot_release_board.py` to verify the corrected held-shot result against hashed source video, shot intervals, boards, union, and release inputs.
