# Canada–Norway 2022: first frozen full-match transfer

The [transfer plan](TRANSFER-PLAN.md) froze the models, release cue and
evaluation rule before inference on this [official full-match replay](https://www.youtube.com/watch?v=EoSwgOcH71g).
The source and artifact hashes are recorded in
[`FIRST-TRANSFER.json`](FIRST-TRANSFER.json). This is another Beijing 2022
broadcast, so it tests a new match within the production family, not a new
camera layout or independent physical throw F1.

The [official results book](https://curlit.com/PDF/PWG2022_ResultsBook.pdf)
lists 16 shots in each of eight ends, 128 total. The extracted
[numbered-shot ledger](../../official-shot-sequence/pwg2022-canada-norway-official-ledger.json)
and [post-shot diagrams](../../official-shot-sequence/pwg2022-canada-norway-official-boards.json)
preserve that reference. The diagrams contain 128 board snapshots and 446
coloured stone symbols; 17 symbols were flagged for review by the extractor.
The official pages do not give video release times.

| Frozen-run observation | Result |
| --- | ---: |
| Full-video provisional candidates | 142 |
| Candidates linked to a readable broadcast counter update | 100 |
| Candidates without a counter link | 42 |
| Official numbered shots | 128 |
| Clean, colour-concordant counter anchors | 100/128 |
| Cap-only visual candidates | 114 |
| Origin-positive, cap-unconfirmed windows scanned by the held-cap rescue | 32 |
| Extra candidates accepted by the frozen held-cap plus ice rule | 0 |

The cap-only alignment linked 65 of 100 readable counter updates to a shot
window. Adding selected learned-motion tracks raised that to 75; the frozen
following-shot rescue linked 99, and a travel-only counter candidate covered
the last update. This is evidence association, not 100 verified physical
release times: the counter appears after the delivery and can be paired with
the wrong visual episode.

Only end 2 has all 16 official shots represented by clean counter anchors.
There the cap-only rule proposed 16 visual candidates and the monotone delayed
counter matcher paired 15 of them with counters. Its **counter-proxy timing
F1 is 0.9375**, but four of those 15 pairs have conflicting known colours and
two have unknown visual colour. Nine have matching known colour. The unmatched
official shot is end 2 shot 7; one visual candidate remains unmatched. The
held-cap rescue leaves this score unchanged. The remaining ends have only
15, 14, 12, 10, 12, 12 and 9 clean counter anchors respectively; no full-end
proxy F1 is reported for them.

These results expose two separate issues. First, 142 provisional candidates
exceed the 128 official deliveries, so the current full-video ledger cannot
be treated as one accurate event per throw. Candidate-count difference alone
cannot classify individual false events or missed throws. Second, temporal
counter matching can conceal colour or shot-identity mistakes. A post-score
frame check of several conflicts showed yellow delivery stones in at least
some windows for which the adjacent-motion cap rule chose red; red clothing
or other red objects are plausible contaminating tracks. One red-stone frame
also indicates that delayed-counter pairing itself can assign the wrong
official shot. Neither possibility is corrected in this frozen result.

The next detector iteration should retain the moving object's image position
and separate the delivery stone from people and graphics using an ice-region
gate and a continuous track across the camera handoff. It should also perform
one-to-one sequence assignment with explicit colour conflicts and abstentions.
After changing those rules, a different untouched recording is required for
a new transfer. Complete-recording precision, recall and F1 still require an
independent timestamped throw reference or an equivalent exhaustive review.

## Post-transfer spatial diagnostic (not a revised first score)

After preserving the frozen result, a separate
[`delivery-ice-cap-diagnostic.json`](../../curlobserver-learned-probe/canada-norway-full-transfer/delivery-ice-cap-diagnostic.json)
rescanned all 146 origin-positive shot windows using lower-ice geometry and
white-ice support. It found sustained spatially gated tracks in 54 windows.
Only 52 of the original 114 cap-confirmed candidate windows retained any
gated colour track, and only 37 retained a track of their original known
colour. Thus this simple ice gate is too destructive to use as a hard event
veto. The source is now exposed development data; this diagnostic is not a
new held-out result or an improved throw F1.

## Post-transfer sequence and view-context audit

The [official-order diagnostic](POST-TRANSFER-SEQUENCE.json) fixes the 100
clean counter-to-shot links, then finds minimum-cost monotone assignments for
the remaining candidates. Among 142 candidates, 112 have the same assignment
in every optimum, 16 are skipped in every optimum, and 14 remain ambiguous.
Among 128 official shots, 112 have the same assignment in every optimum, six
are unmatched in every optimum, and ten remain ambiguous. These statuses
depend on official shot order, inferred end partitions and alignment costs.
They identify review priorities; they are **not** verified event outcomes or
a deployable detector output.

A separate [source-only view-context sidecar](POST-TRANSFER-VIEW-CONTEXT.json)
sampled three frames inside every candidate window. It detected an overhead
house view in 13 of 142 candidate windows, including four of the 16
official-order skipped candidates **and seven counter-backed candidates**.
This confirms that overhead context helps explain some extras but cannot be
used as a blanket rejection rule: real deliveries may continue into an
overhead view, and most skipped candidates had no detected overhead house.
Source frames from the skipped set also include player close-ups and settled
stones. The next rule needs object-level continuity and phase context rather
than a static camera-view veto.

A further [source-only ice-coverage audit](POST-TRANSFER-ICE-COVERAGE.json)
sampled each candidate window at three interior times. Among visual-only
candidates, the median full-frame white-ice fraction was 0.286 for the 16
sequence-skipped candidates and 0.254 for the 12 candidates with the same
official assignment in every optimum. The ranges overlap substantially
(0.047–0.444 versus 0.103–0.299). Lower-half and central-lower fractions
also overlap. This scene-level cue does not separate the groups well enough
for a hard throw decision. It was measured after the first transfer and is
development evidence only.

## Post-transfer public-box model swap

A [revised stone-box model](../../curlobserver-learned-probe/public-tracking-v2/README.md)
improved colour-aware box F1 from 0.681 to 0.859 on 20 clip-split public
tracking videos. A subsequent [targeted audit](../../curlobserver-learned-probe/public-tracking-v2/norway-end2-targeted-transfer.json)
checked whether that component gain helps the exposed Canada–Norway end-2
colour conflicts. In four yellow-counter windows, it removed a supported
red track from one, still produced red tracks in two, and produced no
supported yellow track in any. It did recover a yellow track in a separate
yellow agreement control. A source frame at 1399 s shows a yellow stone near
the bottom edge of a conflict window; the revised model proposes yellow
patches nearby but rejects them below threshold while accepting red boxes
elsewhere. The public-box gain therefore does not yet transfer reliably to
this broadcast side view. This was selected after the frozen transfer and is
not a new event score or evidence of corrected full-match F1.

## Post-transfer short-cap and cross-view pairing study

The [broadcast cap-verifier study](../../curlobserver-learned-probe/cap-patch-crossmatch-v1/NORWAY-ORIGIN-RECEIVER.md)
tests a different route: a frozen broadcast-specific cap-patch model, brief
coherent cap motion, and one provisional origin-to-next-view event candidate.
On exposed end 3, 71 short local transits appeared in 38 of 64 camera shots.
The provisional pairing reduced this to 17 events and associated 14 with all
14 clean delayed counter updates, with matching colour. The pairing rule was
developed on this exposed end and the matcher has two official shots without
clean counter anchors, so this is not full-end F1.

The frozen visual rules were then transferred to end 4. They produced 15
provisional events. Only ten paired with the 12 clean counters; six had
matching colour and four conflicted. Two clean counters and five candidates
remained unpaired. This first transfer shows that the apparent end-3 success
does not generalize reliably to the next end, even within one match. Several
colour conflicts arise from receiving-view-only evidence, where another
stone can move after impact. No full-match event claim is changed.

## Post-transfer mirrored virtual-line study

The [mirrored early-ice gate study](../../curlobserver-learned-probe/cap-patch-crossmatch-v1/MIRRORED-GATE.md)
tested a delivery-side virtual line. A right-side gate retrospectively
resolved all 12 clean end-4 counter colours, then failed on end 5 when the
delivery view flipped left: only two candidates were emitted from 15
origin-positive camera shots, with one wrong-colour counter pair. A left-side
gate was fitted after that failure, and a source-only motion router was
frozen before end 6. The first end-6 transfer emitted 19 coloured candidates
for 16 official throws; 12 paired with clean delayed counters, but only ten
had matching colour and two conflicted. Source frames show held yellow stones
before broadcast cuts and later red non-stone motion cues. The virtual line
helps on visible side views but cannot by itself solve camera orientation,
early cuts or persistent stone identity. No independent event F1 is claimed.

## Post-transfer apparent-cap-size check

The [Norway 2022 prior-cap-area transfer](../../official-shot-sequence/NORWAY-2022-CAP-AREA-TRANSFER.md)
applies a size gate fixed after the China 2022 source diagnosis to 169
shot-scoped cap-track candidates in this recording. It raises unique
next-half-second geometric choices from 18 to 108, while 19 shot-boundary
cases abstain under both rules. Source frames confirm one recovered moving
yellow stone, but also reveal non-stone tracks in the candidate catalog.
These counts do not measure physical-stone identity or throw precision and
recall; this source was previously exposed during development.
