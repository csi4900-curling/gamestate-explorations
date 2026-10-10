# Frozen two-channel agreement transfer

The first 900–1200 s China transfer had one missed coarse red throw. Its
learned-box and cap tracks occupied nearly identical positions over 23 common
frames, but each failed a separate single-channel screen threshold. A
development pair rule was fitted on that exposed miss: both tracks must be
same-colour, have at least five >4 px motion steps and live-overlay support;
the cap track must have local-ice fraction at least 0.7; at least eight common
sample times must have median centre separation at most 15 px. A qualifying
pair is added only when no accepted event is within 20 seconds. Its event
timestamp is the cap track's first observation. This retrospectively changes
that interval from 4/0/1 to 5/0/0 with correct colours; it adds no event in
the two earlier exposed China intervals. These are postscore findings.

Freeze the rule before running a cap scan on the previously exposed
Slovakia–USA G03 6000–6300 s positive gap and China 0–290 s opening negative
segment. Their learned-box tracks and source-only references already exist.
These checks probe extra-event behaviour and limited transfer, not independent
full-recording validation. Preserve first transfer outputs.

- Pair model SHA-256: `3409bebb7c6ecad693c1d5ed736d4b884edb8c8f90f0c20ec6688a90700684b9`
- Pair runner SHA-256: `b49a7fa2f064609d70bd426ebba8898d4ebe9eaa7980d70899feb37a930a68d8`

First preserved transfer: Slovakia–USA G03 yielded 69 raw cap tracks, three
cap-screened candidates, 12 agreeing raw pairs, and zero new event additions
after the 20-second duplicate gate. The scored interior 6030–6300 s reference
remained 2 TP / 0 FP / 0 FN, colour-aware also 2/0/0. China 0–290 s yielded
33 raw cap tracks, zero cap-screened candidates, zero agreeing pairs and zero
emitted events against an empty source-only reference. An additional exposed
Sweden–Switzerland G01 gap yielded one agreeing pair but no new event and
remained 1/0/0. These tests do not establish recall outside their few coarse
windows or full-match precision.
