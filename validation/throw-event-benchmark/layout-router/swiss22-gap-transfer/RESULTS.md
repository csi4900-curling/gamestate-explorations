# Frozen first visual-gap transfer

The scanner and 3900–4200 s source-only reference were frozen in
`SELECTION.md` before scanner inference. The first unchanged pass emitted four
unconfirmed visual tracks against one coarse red delivery window:

| TP | FP | FN | Candidate precision | Candidate recall | Candidate F1 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 3 | 0 | 0.25 | 1.00 | 0.40 |

`G01-R01` starts at 3913 s and matches the red delivery. `G01-R02` at
3927–3936 s is another track of that delivery after a camera/view change;
`G01-Y01` at 3928–3936 s follows a yellow stone moving after the red-stone
interaction, not another delivery. `G01-R03` at 3977–3982 s occurs during a
crowd shot and is a non-stone false candidate. These are post-score source
audits, not changes to the blind reference or first score. Coarse source-only
stills may miss other deliveries, and one gap cannot establish generalization.

The candidate screen therefore has useful recall but inadequate precision.
Temporal grouping of contiguous tracks and a broader ice-scene check are
development ideas fitted on this exposed gap; any resulting score here is
in-sample and needs another source-only frozen transfer.

The resulting development scene/episode screen retained `G01-R01` and
withheld the other three tracks, giving 1/0/0 against this **same exposed**
single-window reference. It was frozen before the Slovakia–USA transfer, where
it scored only 4/3/3 across seven coarse windows (candidate F1 0.571).
