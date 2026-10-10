# Frozen monotone-counter transfer audit

The one-row-rise guard in `prototype/broadcast_scoreboard.py` was developed
after reviewing Canada–China 2022. Before inspecting the other full-match
counter observations, select the complete Slovakia–USA and
Sweden–Switzerland 2022 counter audits already saved under
`validation/curlobserver-learned-probe/`. Replay each saved one-second
observation stream through the current model, preserving the input and code
hashes. Compare colour/timestamp event keys against each source's prior
counter replay and report removals, additions and unresolved counts.

No parameter changes are allowed after this transfer comparison without
making a new development revision. A counter-key change is a regression
signal requiring source review; an unchanged key list is only stability
evidence. These counter audits are not independent throw references, and
whole-recording F1 cannot be calculated from them.
