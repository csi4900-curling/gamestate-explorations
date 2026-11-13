# Korea–China full-match isolated-edit development run

This is an **unfrozen development comparison**, not independent throw-event validation. It reuses the same 6,829 s source, frozen origin model, and frozen motion models as `../korea-china-full-first-transfer/`, but adds 42 source-only, temporally isolated possible camera edits to the 524 conservative hard cuts. The resulting shot review has 567 windows versus 525 in the first pass. The original first-pass outputs were not changed.

| Measure | Frozen first pass | Augmented development run |
| --- | ---: | ---: |
| Camera-shot windows | 525 | 567 |
| Positive origin windows | 98 | 103 |
| Final candidate events | 103 | 102 |
| Counter-backed candidate events | 81 | 81 |
| Official shot count (order-only reference) | 96 | 96 |

The five additional positive origin windows **do not** constitute five recovered throws. A new cut can also split or remove a candidate. The two ledgers have different intervals and IDs after each added cut, so candidate IDs are not comparable across runs. All 81 counter IDs are represented in both ledgers, but counter association and colour can change.

The specific S372 failure is partly rescued. The first pass treated 5170.8–5206.2 s as one origin window and put yellow candidate T085 there. The augmented run splits at 5195.6 s: the early window 5170.8–5195.6 scores 0.0086 for origin, while the later 5195.6–5206.2 scores 0.9580 and yields a separate **red** visual candidate. Source-frame inspection supports a new red delivery here. This is not independently labelled proof of that event.

The global result does **not** justify promoting all 42 possible edits into the production cut rule. The ledger loses one net candidate; among the 81 counter-backed events, B08, B63, and B71 lose a previously assigned colour, while B67 gains yellow. B71 moves from the long yellow S372 window to an earlier candidate with unresolved colour. Those associations need source review before interpreting them as improvements or regressions. The provenance-checked [ledger comparison](ledger-comparison.json) matches counter-backed events by counter ID and leaves visual-only candidates unmatched: interval overlap alone cannot establish physical identity when an old window may contain two throws. The 96-shot official count has no source-video event timestamps, so this run does not establish precision, recall, or F1.

The [multiscale event handoff](multiscale-event-handoff.json) carries both segmentation results without forcing a winner. It has 81 counter-backed hypotheses, with 69 having the same **known** colour in both runs, 12 unresolved, and 51 having an identical release-window bound. It also preserves 43 visual-only proposals across the two runs without pretending that overlapping intervals prove duplicate identity. For B71 it retains the original yellow 5170.8–5206.2 s observation and the new unresolved 5142.0–5151.8 s observation as alternatives; the red 5195.6–5206.2 s candidate stays separate. All exact release/settle times and simulation-readiness fields remain unknown or false.

The [cut-effect audit](cut-effect-audit.json) classifies local origin-model response at all 42 added points: 28 move an existing positive into the right-hand window (`101`), nine leave both windows negative (`000`), three have a positive old window but neither immediate child positive (`100`; other cuts in the same old window can matter), and two turn a previously negative old window into a positive right-hand window (`001`). These are model-response patterns, not independently verified throw gains or losses.

The [visual-only patch diagnostic](visual-only-patch-evidence.json) finds at least one stone-like cap track for nine of 21 unbacked candidate windows; 12 lack such support. It does not change the candidate ledger or verify a physical throw.

The [joined visual-only cue table](visual-only-evidence-patterns.json) records seven candidates with both stone-like patch and unique colour-compatible held-release passage, two with appearance only, two with release only, and ten with neither. The new red T085 at 5195.6–5206.2 s is in the **neither** group. This is direct evidence against using the two-cue rule as a hard event filter: this source-supported cut rescue would be suppressed.

Reproduce with `feasibility/scripts/python.sh prototype/scripts/run_full_shot_evidence.py --video validation/throw-event-benchmark/paralympics-2022-korea-china/source.mp4 --source-id ia3HIF_4Bdo --start 0 --end 6829 --origin-model validation/curlobserver-learned-probe/shot-origin-pair-v1/model-excluding-swiss-dev.npz --learned-model validation/curlobserver-learned-probe/model-v1/model.npz --edit-audit validation/curlobserver-learned-probe/korea-china-full-first-transfer/possible-edits-0_30-temporal.json --output validation/curlobserver-learned-probe/korea-china-edit-augmented-development`. The runner resumes matching existing artifacts and refuses mismatched source, span, code, or edit-audit hashes.
