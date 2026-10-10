# Canada–China 2024 same-production transfer

The source-only reference was frozen before candidate inference. It contains 18 coarse delivery windows over 1650–2760 s. The first frozen bidirectional detector produced 26 candidates: 17 matched deliveries, 9 unmatched candidates, and 1 missed delivery (precision 0.654, recall 0.944, F1 0.773). The previously chosen x=160±60 corridor retained 21 candidates: **17 TP / 4 FP / 1 FN**, precision 0.810, recall 0.944, F1 0.872. All matched colours were correct. Neither first-pass result meets the high-precision/high-recall target. Scores and predictions are preserved in `frozen-first-*.json`.

Post-score source review found the missed C01 red stone visible in positive-y motion at 1686.0–1687.8 s. It is first recognized at y≈61, just past the y=60 gate; no tracked point can cross that line. This is a gate-placement miss, not an absent delivery. The four accepted false events are D03 and D05 at 1795/1814 s during end changeover, D11 at 2048 s during the genuine yellow delivery's aftermath, and D23 at 2608 s after a genuine red delivery. The last two tracks follow moving players/equipment despite strong colour and neutral-body mask support. Corridor and cap/body appearance alone cannot establish a delivered stone.

The reference comes from source-only still sheets reviewed by the same agent, at 5 s with 2 s dense patches. It is neither independent human validation nor proven exhaustive continuous-video labelling. This interval is now development data. Any later score here is in-sample; a new untouched source must be chosen before another transfer claim. The 2022 Beijing camera family requires its separate scoreboard/layout adapter and cannot inherit this fixed-panel gate.

Moving the gate from y=60 to y=80 recovers C01 and yields 18 TP / 2 FP / 0 FN here (precision 0.90, recall 1.00, F1 0.947). It is **not** a general replacement: the same change on the already-exposed Canada–Italy interval yields only 9 TP / 3 FP / 8 FN (F1 0.621), down from its y=60 corridor development result of 17 / 0 / 0. The later gate loses many stones that are first recognized beyond y=80. Both post-score outputs are retained as `development-gate80-*.json`. Multi-gate candidate fusion is being examined rather than promoting this failed single-line change.

The experimental y=60+y=80 union, merging same-colour/same-direction crossings within 4 s and 20 px, recovers all coarse labels on both exposed 2024 intervals. It also scores **18 / 5 / 0** here (precision 0.783, F1 0.878) and **17 / 4 / 0** on Canada–Italy (precision 0.810, F1 0.895). This is not a promotion candidate. The extra line adds apparent throws from moving people and equipment, including candidates close to genuine events. It illustrates that raising recall by pooling weak passage evidence degrades precision unless a camera/end-phase model and independent stone-motion signal filter the candidates.

A subsequent same-layout confirmation rule screens slow passages, competing
passages within 15 s, and isolated reversed camera motion. It scores 18/0/0
here and 17/0/0 on Canada–Italy. **Both are in-sample fits**, because their
false events informed the rule. The exact rule and code fingerprints were frozen
before the next Canada–Estonia source was downloaded or inspected; see its
`SELECTION.md` for the transfer protocol. No high-F1 generalization conclusion
follows from these two 1.00 scores.
