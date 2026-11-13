# Canada–Czechia 2024 RR9: frozen first transfer

This is the first unchanged combined transfer of the [precommitted plan](TRANSFER-PLAN.md) to catalogue source `yu_YoFrFd20`, source seconds **1650–2760**. It is a candidate accounting and provenance result, **not** an event accuracy result. There are no independent exhaustive throw labels for this interval, so precision, recall and F1 are unknown.

A prediction-free [throw-only review packet](blind-throw-review/README.md) and [seal/score workflow](EVALUATION-WORKFLOW.md) are ready for a teammate to label this exact 18.5-minute interval. No labels have been received or scored. This review would assess throw-event detection only; settled-board and metric-position validation remain separate.

A separate [postscore full-match stage-one sweep](FULL-MATCH-STAGE1-RESULTS.md) covers all 6683 source seconds: 147 raw spans, 116 in the fixed corridor, and 31 withheld. The subsequent [full-match high-resolution screen](FULL-MATCH-STAGE2-RESULTS.md) retained 79 provisional candidates; source review already found one accepted postgame false positive. These are not verified throws or a measured full-match F1. All 24 raw candidates in this frozen interval reconcile exactly with the full-match scan.

An unchanged, newer [source-diverse side-view patch transfer](RIGHT-SOURCE-DIVERSE-PATCH-TRANSFER.md) also scores all 131 existing full-match right-camera proposals. It marks 94 stone-like at one or more sampled points. Same-agent source-pixel audits found that all 23 right-only sampled prefixes follow people or wheelchairs (22 negative, one shirt false positive), 15 negative left-linked prefixes follow people/equipment, and one positive ambiguous prefix follows a stone. A separate fixed sample of 20 positive one-to-one links all shows moving-stone pixels; 70 such links remain unsampled. These are useful appearance checks, not independent event validation or a reason to erase unresolved hypotheses.

The [source-diverse episode-state handoff](SOURCE-DIVERSE-EPISODE-STATE-HANDOFF.md) now joins that appearance evidence and a [cross-resolution image-path check](CROSS-RESOLUTION-PATH-OVERLAP.md) to all 133 existing cross-view episodes and their partial boards without dropping any of the 116 left or 131 right candidates. Forty-two temporal pairs have two or more exact shared source times and close receiving-camera image centers, but a known person path also agrees closely across resolutions. Its priorities make competing or unreviewed paths inspectable while every physical identity, complete game state and simulation-ready flag remains unresolved.

The [reviewed-stone replay gap ledger](REVIEWED-STONE-REPLAY-GAPS.md) isolates 21 source-reviewed moving-stone prefixes. Seven also have shared-time image-path agreement and a partial board; two of those boards do not contain a same-colour local stone observation. A 12-case source-pixel inventory now covers every reviewed prefix with both a moving-path endpoint and a later same-colour board observation: 10 cases contain multiple same-colour components in at least one sampled crop. A board-blind cap continuation reaches the first same-colour board-observation time in four cases; three end within 1.1 image pixels of a board-frame red detection, while E096 is 446 pixels from its first red detection because that detection belongs to an existing stone. The [later-onset probe](full-reviewed-later-board-onset-probes-development.json) finds E096's cap 0.34 pixels from the later red observation, but E080's continuing cap 343.9 pixels from its later red observation. The [additive evidence handoff](full-reviewed-stone-continuation-handoff-development.json) preserves all 21 cases and records E096's late board link as a hypothesis only. Persistent identity and complete game state remain unverified, identifying the association and board-linking work needed before a simulation can represent a complete throw.

The full 360p source fingerprint is `e63c9b063b5b11ad5173083dffe974d909c78e5d01312740b87bccc006402013`; the separate 1080p interval fingerprint is `6d3f489b7b908281bca9a52eb85470d95374f65f328c13e1e6daf6cbb8bf6623`. Six predeclared cross-resolution checks found zero best time adjustment. The [frozen components](frozen-components.json) and [machine verification](verification-frozen-first.json) pin the exact code, model, calibration, sources and stage inputs. The verifier checked every candidate ID through the chain and returned **24 → 19 → 15**.

| Stage | First-pass result |
| --- | --- |
| 10 Hz source span proposals | 24 raw |
| Fixed left-panel corridor, x = 160 ± 60 px | 19 retained; 5 withheld |
| Fixed 10 s right-anchor grid | 30/111 registered against original reference; selected source second 1685 from a 26-frame pose cluster |
| Initial receiving motion | 12 unique paths; 7 unsupported |
| Same-shot registration hold | 14 unique, 4 unsupported, 1 ambiguous; 44 borrowed registration samples |
| Bounded-gap selection | 15 unique, 3 unsupported, 1 ambiguous |
| Conditional dropout rescue | 15 baseline paths preserved; 3 abstentions; 1 shared-prefix-only path |
| Frozen patch and duplicate screen | **15 provisional events**, 3 unsupported abstentions, 1 duplicate |

The duplicate is **S13**, whose 19-sample ambiguous shared prefix overlaps **S12** at 14 timed path observations. It is retained in the decisions, but it is not counted as a second event. S04–S06 abstain because no supported receiving motion path survived. All 19 corridor IDs remain visible in the [screen decisions](conditional-dropout-screen-frozen-first.json); the five off-corridor raw IDs remain in the [corridor artifact](frozen-first-span-corridor.json).

A separate [postscore source review](POSTSCORE-END-RESET-REVIEW.md) found that S04–S09 cluster around a visible end reset: players and implements move through the left view, stones are collected, and the broadcast scoreboard changes soon after. All six were already rejected or withheld by the frozen pipeline. This is a useful failure-mode check, not an independent estimate of specificity or recall.

These are provisional video proposals. A motion path and patch match do not prove a physical throw, exact release or settle time, persistent stone identity, calibrated metric accuracy, complete board state, or rotation count. The trajectory's center coordinates alone cannot determine revolutions; that requires visible handle or stone orientation tracked over dense frames. None of these events is simulation-ready. Independent full-interval labels and source-frame error review are required before any high-precision or high-recall claim. Post-event partial-board reconstruction remains a separate next stage; it should not silently fill unobserved state.

## Postscore partial-board observation

The [full-match partial-state sequence](full-match-partial-state-sequence-postscore.json)
now joins the 79 accepted passage candidates to their post-event video board
observations and adjacent-board comparisons. It contains **66** candidates
with at least one stable, camera-local stone observation and **40** adjacent
same-camera partial comparisons. The 37 screen-withheld candidate IDs remain
explicit, and comparisons with intervening candidates, missing boards or camera
changes remain abstentions. All 79 entries have `simulation_ready: false` with
machine-readable blockers; an observed position is a conditional 2D estimate,
not a complete state or evidence of a physical stone addition or collision.
Both known agent-reviewed false paths, S96 and S143, remain in the frozen
candidate count but carry source-review flags and an extra simulation blocker.
Those reviews are not independent exhaustive labels.
The [offline viewer](../../../prototype/full-match-canada-czech-state/index.html)
links each observation and transition to its source-video time; its plots show
camera-local proposals only. [Viewer provenance](../../../prototype/full-match-canada-czech-state/provenance.json)
pins the input and renderer hashes.
The later [91-candidate development branch](LEFT-BOUND-STATE-HANDOFF.md)
has a separate [replay viewer](../../../prototype/full-match-canada-czech-state-development/index.html).
It preserves every frozen board observation while adding 12 candidate paths;
neither branch has independently measured full-match F1.
Reproduce from the source-hashed component files with:

```sh
python prototype/scripts/export_partial_state_sequence.py \
  --screen validation/throw-event-benchmark/canada-czech-2024/full-match-screen-postscore.json \
  --boards validation/throw-event-benchmark/canada-czech-2024/full-match-partial-boards-postscore.json \
  --comparisons validation/throw-event-benchmark/canada-czech-2024/full-match-adjacent-boards-postscore.json \
  --source-review validation/throw-event-benchmark/canada-czech-2024/source-review/s96-review.json \
  --source-review validation/throw-event-benchmark/canada-czech-2024/source-review/s143-review.json \
  --output /tmp/canada-czech-partial-state-sequence.json
```

After freezing the screen, the unchanged [quiet-tail board scan](post-event-partial-boards-postscore.json) found a stable, view-local partial board for **12 of 15** proposals. Two eligible tails had no stable stone proposals; S12 had too little quiet time before the next candidate. Across the scan, 277 tail frames registered and 58 abstained. The 12 boards contain 69 local stone proposals in total, counted separately at each observation time; **69 is not a count of distinct physical stones**. This is postscore development, not part of the frozen throw screen. No board is complete or simulation-ready, and there is no physical identity link between successive boards.

The [adjacent-board ledger](adjacent-partial-board-comparisons-postscore.json) compares consecutive accepted proposals while checking *all* intervening passage candidates, including the five withheld by the corridor. It permits eight same-camera partial comparisons with **40 nearby same-colour observation pairs**. Four transitions abstain for a missing board, one for a camera change, and one for an intervening candidate. The pairs are conditional spatial associations only: neither same-end continuity nor physical stone identity has been verified. Missing or unmatched detections do not establish additions, removals, collisions, or a scoring state.

The [evidence-state handoff](evidence-state-handoff-postscore.json) now preserves all **24 raw candidate IDs** in one timeline: 15 provisional events, four screen abstentions, and five outside-corridor candidates. The 15 events carry conditional motion and board observations; the other nine remain visible without fabricated event state. The separate [official result context](official-end-score-context.json), transcribed from page 43 of the locally pinned 2024 results book, records six completed ends and final totals Czechia 4, Canada 13. It provides end-score constraints, **not** event timestamps or video-to-end assignments. Every handoff row has unknown end identity and spin count; all 24 remain non-simulation-ready.

The unchanged 2024 [broadcast marker scan](end-marker-full-postscore.json) reads a marker in **335 of 669** ten-second full-match samples and recognizes an end **2 → 3** display change between sampled seconds 1940 and 1970. [Local candidate alignment](end-display-context-postscore.json) brackets 22 of 24 raw candidates within a displayed end; S09 and S10 straddle the graphic change. The [augmented handoff](evidence-state-with-display-postscore.json) attaches this source context to every candidate while preserving unknown physical end identity and simulation status. A displayed end may lag the first delivery in that end, so the marker cannot resolve S10's physical end by itself.

The full-match marker scan also contains an isolated **5 → 4 → 5** reversal near 4870 s outside this transfer interval. The existing [two-hit temporal summary](end-marker-temporal-summary-postscore.json) discards that one-hit end-4 reading and retains six ordered displayed-end runs, consistent with the official six completed ends. This still does not locate physical end boundaries or establish shot counts.

Reproduce the integrity check with:

```sh
feasibility/scripts/python.sh prototype/scripts/verify_conditional_dropout_transfer.py \
  --directory validation/throw-event-benchmark/canada-czech-2024 \
  --output /tmp/canada-czech-transfer-verification.json
```

The verifier checks source fingerprints, frozen component hashes, stage links, candidate conservation, accepted-event accounting and simulation-ready flags. It does not inspect whether a proposed event is actually a throw.

The postscore board stages can be reproduced independently from the frozen files:

```sh
feasibility/scripts/python.sh prototype/scripts/audit_rebased_post_event_partial_boards.py \
  --video validation/throw-event-benchmark/canada-czech-2024/source-1080p-1650-2760.mp4 \
  --candidates validation/throw-event-benchmark/canada-czech-2024/frozen-first-span-corridor.json \
  --screen validation/throw-event-benchmark/canada-czech-2024/conditional-dropout-screen-frozen-first.json \
  --motion validation/throw-event-benchmark/canada-czech-2024/conditional-dropout-rescue-frozen-first.json \
  --hold validation/throw-event-benchmark/canada-czech-2024/fixed-grid-hold-merged-frozen-first.json \
  --source-motion validation/throw-event-benchmark/canada-czech-2024/fixed-grid-motion-merged-frozen-first.json \
  --output /tmp/canada-czech-post-event-boards.json
feasibility/scripts/python.sh prototype/scripts/audit_adjacent_partial_boards.py \
  --boards /tmp/canada-czech-post-event-boards.json \
  --candidates validation/throw-event-benchmark/canada-czech-2024/frozen-first-span-corridor.json \
  --screen validation/throw-event-benchmark/canada-czech-2024/conditional-dropout-screen-frozen-first.json \
  --output /tmp/canada-czech-adjacent-boards.json
feasibility/scripts/python.sh prototype/scripts/export_rebased_evidence_state_handoff.py \
  --candidates validation/throw-event-benchmark/canada-czech-2024/frozen-first-span-corridor.json \
  --screen validation/throw-event-benchmark/canada-czech-2024/conditional-dropout-screen-frozen-first.json \
  --motion validation/throw-event-benchmark/canada-czech-2024/conditional-dropout-rescue-frozen-first.json \
  --hold validation/throw-event-benchmark/canada-czech-2024/fixed-grid-hold-merged-frozen-first.json \
  --source-motion validation/throw-event-benchmark/canada-czech-2024/fixed-grid-motion-merged-frozen-first.json \
  --boards /tmp/canada-czech-post-event-boards.json \
  --comparisons /tmp/canada-czech-adjacent-boards.json \
  --official-end-scores validation/throw-event-benchmark/canada-czech-2024/official-end-score-context.json \
  --output /tmp/canada-czech-evidence-state-handoff.json
feasibility/scripts/python.sh prototype/scripts/scan_2024_end_markers.py \
  --video validation/throw-event-benchmark/canada-czech-2024/source-360p.mp4 \
  --step-s 10 --output /tmp/canada-czech-end-markers.json
feasibility/scripts/python.sh prototype/scripts/summarize_end_marker_scans.py \
  --scans /tmp/canada-czech-end-markers.json \
  --output /tmp/canada-czech-end-marker-summary.json
feasibility/scripts/python.sh prototype/scripts/align_transfer_end_display.py \
  --raw validation/throw-event-benchmark/canada-czech-2024/frozen-first-span-raw.json \
  --marker-scan /tmp/canada-czech-end-markers.json \
  --output /tmp/canada-czech-display-context.json
feasibility/scripts/python.sh prototype/scripts/attach_display_context_to_handoff.py \
  --handoff /tmp/canada-czech-evidence-state-handoff.json \
  --display-context /tmp/canada-czech-display-context.json \
  --corridor validation/throw-event-benchmark/canada-czech-2024/frozen-first-span-corridor.json \
  --output /tmp/canada-czech-evidence-with-display.json
```
