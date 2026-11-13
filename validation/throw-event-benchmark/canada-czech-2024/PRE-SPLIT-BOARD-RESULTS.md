# Partial boards after six withheld motion windows

The existing quiet-tail observer was run on the six [pre-split motion review
proposals](PRE-SPLIT-PROPOSAL-RESULTS.md), with the **full 116-candidate corridor
list** bounding each tail. Five windows yielded a stable partial board. S131
initially had no eligible tail because S132's duplicate early trigger at
5722.052 s occurs before the shared receiving prefix ends at 5724.5 s.
The [deduplicated tail-clock input](gap-review/s131-dedup-tail-input/manifest.json)
removes S132 only from this board-observation clock after verifying its exact
prefix match; it leaves the raw timeline and both event screens unchanged.
That replay yields S131's partial board. The [merged six-row board artifact](gap-review/pre-split-partial-boards-development.json)
records both observer outputs and the deduplication provenance.

| Window | Tail endpoint | Stable proposals | View-local colours | Tail-clock note |
| --- | ---: | ---: | --- | --- |
| S33 | 1108.0 s | 3 | 3 red | Full candidate clock |
| S40 | 1548.0 s | 4 | 4 red | Full candidate clock |
| S80 | 3312.0 s | 5 | 4 red, 1 yellow | Full candidate clock |
| S84 | 3611.0 s | 4 | 3 red, 1 yellow | Full candidate clock |
| S90 | 3923.0 s | 4 | 3 red, 1 yellow | Full candidate clock |
| S131 | 5755.0 s | 4 | 3 red, 1 yellow | Exact duplicate S132 omitted from tail clock |

The [six source frames at the tail endpoints](gap-review/pre-split-board-tail-source-review.jpg)
are a necessary visual control. In S40's 1548.0 s frame, a **yellow stone is
visibly present in the house**, while the stable-board observer reports only
four red proposals. Thus `partial_stable_view_local_board` means there are
repeated stable detections, **not that all visible stones were found**. Other
frames contain occlusions and player-adjacent objects; this sheet is not an
exhaustive independent stone annotation. No reported board count should be
used as an official score or full game state.

A broader [source check of unusual proposal shapes](BOARD-OBJECT-FAILURES.md)
also found player hats and jersey logos among the original stable proposals.
A stationary-suffix replay recovers S40's yellow stone but adds a hat in S131,
so that development rule was not adopted. One similarly shaped S90 proposal
is a real stone behind a wheelchair; a simple shape threshold is unsafe.

The [interactive pre-split board viewer](left-bound-full-match/pre-split-board-review/index.html)
places each partial path, quiet-tail board, source video, and source-review
frame together. Its V-number observations are local to one candidate window;
they do not assign persistent physical stone identities or connect across
throws. The source-visible S40 omission illustrates why a simulation cannot
yet be initialized from these boards without stronger detection and explicit
unknown-stone handling. Release and settle times, contact outcomes, camera
geometry error, scores, and spin remain unverified.
