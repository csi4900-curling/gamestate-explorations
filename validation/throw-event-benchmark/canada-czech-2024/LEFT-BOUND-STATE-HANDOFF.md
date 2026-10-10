# 91-candidate partial-state handoff after left-bound development replay

The [integrated screen](left-bound-full-match/integrated-screen-development.json) retains 91 **provisional candidates**: the frozen 79 plus 12 newly selected left-view stone paths. The [separate interactive review page](left-bound-full-match/review/index.html) lets a reviewer seek the full source video and inspect each candidate's path and partial board. The existing post-event quiet-tail observer was run only for those [12 added candidates](left-bound-full-match/added-partial-boards-development.json), using the same full 116-candidate passage list to bound each tail. All 12 yielded a `partial_stable_view_local_board`; this is stable visual evidence, not a verified complete post-throw board or proof that the delivered stone has settled.

The [91-row board ledger](left-bound-full-match/integrated-partial-boards-development.json) interleaves the 12 new rows with the **unchanged 79 frozen board rows** in candidate order. Its statuses are 78 partial stable boards, nine registered tails without stable stones, and four tails with no usable quiet interval. The [147-raw-candidate timeline](left-bound-full-match/integrated-evidence-with-boards-development.json) preserves every rejected/withheld candidate and explicitly marks the two agent-source-reviewed wheelchair false paths S96 and S143, which still remain in the candidate screen. It has 89 unreviewed provisional candidates, 25 screen abstentions, and 31 outside-corridor raw candidates. These categories are not independently scored throw truth.

The [unified event-to-state sequence](left-bound-full-match/partial-state-sequence-development.json)
joins all 91 candidates to their post-event partial observations and adjacent
comparisons with source/input/code hashes. An exact ID-keyed comparison against
the [frozen 79-event sequence](full-match-partial-state-sequence-postscore.json)
found **79/79 identical post-event board observations**. Nine prior transition
rows change because the 12 added candidates alter adjacency; those transitions
are recomputed rather than inherited. All 12 new candidates have a nonempty
stable partial board, and the integrated sequence has 56 comparable transitions.
The [development replay viewer](../../../prototype/full-match-canada-czech-state-development/index.html)
shows the source video and both adjacent partial observations for each candidate.
The known S96 and S143 wheelchair false-path reviews are attached separately
with source hashes and remain within the 91-candidate count. This is a visual
evidence browser, not a verified throw or physics replay.

The unchanged [adjacent-board comparator](left-bound-full-match/integrated-adjacent-boards-development.json) evaluates the 90 successive accepted-candidate pairs. It makes 56 conditional same-view comparisons and abstains on 34 pairs (17 missing partial boards, 12 intervening raw passage candidates, five camera changes). The [observation-tracklet ledger](left-bound-full-match/integrated-observation-tracklets-development.json) assigns 321 stable stone observations to 149 **camera-local** tracklets using 172 uniquely nearby same-colour associations. No tracklet crosses a camera change or an abstained comparison. A matched observation is not verified persistent physical stone identity; an unmatched observation does not prove a stone appeared or disappeared.

This is a useful representation for review after each candidate, but not yet a complete game state. The boards cover only visible, stable proposals in one view. Candidate misses and the two known false paths can contaminate the sequence. A [path-to-board diagnostic](left-bound-full-match/added-path-board-gap-development.json) finds that the nearest same-colour stable proposal is **0.014–5.961 conditional metres** from the last sampled path point across the 12 additions. The stone may keep moving after that point, so neither a small nor a large gap assigns a physical endpoint. Metric registration error, cross-view alignment, collisions, scoring, exact release/settle times, spin and end identity remain unverified. Every row keeps `simulation_ready: false`. A physics replay or coaching claim must wait for those identities and measurements to be validated.

A later [source audit of six withheld-event quiet tails](BOARD-OBJECT-FAILURES.md)
found a visible yellow stone omitted from one partial board and player hats or
jersey logos among some stable proposals. This directly limits the board
counts above: stability is not stone identity or completeness.
