# Track-context cue transfer plan, frozen before Latvia replay

The Scotland bridge source has already been inspected. Its same-object track
replay and one-pair surrounding-motion diagnostic suggest a tentative
three-way review signal: context that stays fixed around a moving cap versus
context that moves with it. The ring is 12–30 px from the tracked centre in
the 640×360 frame, evaluated at track points nearest to −0.25 and +0.25 s
around passage time. The full-ring comovement index is
`(stationary_mae - track_following_mae) / (stationary_mae + track_following_mae)`.

For development reporting only, call index ≤ −0.20 `isolated_motion_cue`,
index ≥ +0.20 `comoving_context_review`, and everything between
`ambiguous_context`. These cutoffs were chosen **after** Scotland inspection
and cannot be scored as an untouched Scotland improvement. None is a hard
throw acceptance or rejection rule.

Replay the unchanged raw span detector over the saved full-source Latvia
90–6930 s supported run, require exact agreement with its frozen 119 raw
candidates, and preserve every candidate's image track. Apply the same
surrounding-motion code and three cutoffs without changes. Report the cue
distribution across the 72 pre-existing context-accepted and 47 withheld
Latvia candidates. Inspect a fixed five highest-index accepted cases in
source frames only after their ranking is saved. This is another exposed
2024 recording and has no independent timestamped throw reference; it tests
cue stability and failure modes, not event precision, recall or F1.
