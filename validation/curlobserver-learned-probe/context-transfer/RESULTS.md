# First frozen compact-overlay/local-ice transfer

The rule and three follow-up gaps were selected in `SELECTION.md` before the
new candidate or context passes ran. Coarse references came from earlier
agent-authored source-only sheets and were already exposed in other
experiments; these are development candidate scores, not independent throw F1.

| Gap | Raw TP / FP / FN | Frozen screen TP / FP / FN | Screened temporal F1 | Screened colour-aware F1 |
| --- | ---: | ---: | ---: | ---: |
| Slovakia–USA G02, fit gap, 2 windows | 2 / 44 / 0 | 2 / 0 / 0 | 1.000 | 1.000 |
| Slovakia–USA G01, transfer, 3 windows | 3 / 31 / 0 | 3 / 1 / 0 | 0.857 | 0.857 |
| Slovakia–USA G03, transfer, 2 windows | 2 / 22 / 0 | 2 / 0 / 0 | 1.000 | 0.500 |
| Sweden–Switzerland G01, other recording, 1 window | 1 / 81 / 0 | 0 / 0 / 1 | 0.000 | 0.000 |

The other-recording transfer **fails recall completely**. The matching red
track at 3916.2 s is withheld because the broad scoreboard-patch comparison
is 0.234, just over its frozen 0.22 threshold, although the live scoreboard
remains visible. The first-frame template at 3900 s includes the rink/player
background around the compact graphic, and the camera changes to an overhead
ice view. The statistic measures that background change, not only scoreboard
presence. The unchanged local-ice value for this track is 0.523.

G03's apparently perfect temporal count hides a colour error: the frozen
episode selector picks a red track at 6056.2 s over an earlier yellow track
near the source-only yellow delivery. This illustrates why temporal F1 and
colour-aware F1 must both be reported. The raw dense tracker still produces
24–82 candidates per 300-second gap, far above an acceptable confirmed-event
rate; the screen cannot be promoted from these results.

All raw tracks, context decisions, exact hashes and per-gap scores remain in
this directory. The first frozen outputs are not overwritten by later
development changes.
