# Public-label stone-box learning probe — development only

This experiment tests whether published stone boxes can improve the visual
observation layer without asking the user to annotate footage. Later sections
score provisional throw candidates against coarse agent-authored windows;
they do **not** establish validated full-video throw-event F1.

The source is the [CurlObserver dataset](https://github.com/CurlObserver/dataset)
at pinned commit `2cfe61efede3c446957ee94aefa8df1345fc4684`. A fixed random
sample of 300 detection images was selected by seed 20261007, excluding the
25-image earlier probe and a 20-index radius around each of its images. The
selection was written before downloads. The data has no source-match IDs, so
the split cannot establish independence across matches or broadcasts. The
training file hashes and indices are in `train/manifest.json`.

At 640×360, coloured components propose six square box sizes. A compact
gradient/color patch descriptor and balanced linear SVM score those boxes;
class-specific non-maximum suppression removes overlaps. The classifier fit
used 240 images, with 60 images for threshold selection. `model-v2/model.npz`
contains the fitted weights, scaling and threshold, and `model-v2/results.json`
records the image split and code/input hashes. `model-v1` is the first identical
fit; `model-v2` has the current inference-code hash. Their saved model bytes
match exactly.

| Published-box diagnostic | References | Matches | Misses | Extras | Precision | Recall | Box F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Old cap/body heuristic, fixed 25 images | 102 | 8 | 94 | 85 | 0.086 | 0.078 | 0.082 |
| Learned patch boxes, image-level validation 60 images | 214 | 164 | 50 | 33 | 0.832 | 0.766 | 0.798 |
| Learned patch boxes, fixed 25-image development probe | 102 | 78 | 24 | 19 | 0.804 | 0.765 | 0.784 |

The 25 images were already inspected to design the proposal geometry, so the
last row is not a held-out estimate. Box IoU ≥0.5 and same-colour one-to-one
matching are used. The improvement shows public labels are useful for a stone
observation component; 24 misses and 19 extras on just 25 images remain too
large for a high-F1 event claim.

## Broadcast-gap check

The model was then run at five frames per second over the already exposed
Slovakia–USA 2022 G02 gap (3900–4200 s). The frozen coarse source reference
contains one yellow and one red delivery. `g02-dense-motion.json` preserves 46
raw motion tracks, and `g02-dense-screen.json` applies the earlier ice/episode
screen unchanged.

| Stage | TP | FP | FN | Temporal candidate F1 | Colour-aware F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Raw tracks | 2 | 44 | 0 | 0.083 | 0.083 |
| Earlier episode screen | 2 | 3 | 0 | 0.571 | 0.286 |

These are **candidate-to-coarse-window** scores on one exposed gap, not
confirmed event F1. The apparent screened temporal match for the yellow throw
is a red track, and the screen withholds the detected yellow track. Visual
audit at 3965–3969 s showed the long yellow trajectory includes a stone moved
near the house after the delivered stone approached; the greedy tracker merges
identities. A red television graphic also forms a track. The public overhead
box data does not solve delivery origin, camera-cut association or side-view
stone appearance. The learned detector is therefore not promoted to the throw
pipeline.

Recreate the experiment with:

```sh
feasibility/scripts/python.sh prototype/scripts/fetch_curlobserver_train.py \
  --output /tmp/curlobserver-train --count 300
feasibility/scripts/python.sh prototype/scripts/train_stone_patch_probe.py \
  --train /tmp/curlobserver-train \
  --probe validation/curlobserver-probe \
  --output /tmp/curlobserver-model
```

The video probe is `prototype/scripts/probe_learned_gap_motion.py`; its exact
model/source/code hashes and five-hertz tracker parameters are in the output.
## Later dense-gap development

The first screen above failed on camera changes. A compact opaque-scoreboard
check, local-ice check and motion-step requirement were fitted over exposed
Beijing intervals. Their frozen v4 form produced no candidate on two selected
negative intervals (China opening 0–290 s and closing 8100–8356 s). On the
first 300 s of China live play, the first score was 6 TP, 0 FP, 1 FN against
seven coarse agent-authored windows: temporal and colour-aware F1 0.923.
The missed yellow stone was large in a side camera; public CurlObserver
tracking samples inspected so far were overhead, and an expanded classifier
trained on the same public images did not recover it. See
`china-live-transfer/SELECTION.md` and the preserved first score.

A separate multiscale colour-cap tracker found that missing yellow stone.
Its smooth-motion screen was fitted on the exposed missed window and then
scanned across the full 300–600 s interval. On its own it scored 3 TP, 0 FP,
4 FN temporally and only 1 colour-aware TP. A development fusion kept the
primary learned-box events and added screened cap motion only when more than
20 s from any primary event. This retrospectively scored 7 TP, 0 FP, 0 FN on
the exposed 300–600 s interval. `china-live-transfer/MULTISCALE-SELECTION.md`
records the fitted rule and hashes.

Before any detector output from 600–900 s was read, fixed source-only sheets
and a six-window reference for 600–885 s were written and hashed. The frozen
fusion scored 6 TP, 0 FP, 0 FN **temporally**, but only 4 TP, 2 FP, 2 FN
when colour must match (colour-aware F1 0.667). The learned-box component
selected earlier red tracks over later yellow stone tracks twice. This is a
source-only, same-match development transfer, not independent validation or
release-time accuracy. See `china-next-live-transfer/SELECTION.md` and
`frozen-first-fused-score.json`. The reserved Wetzikon source was not used.

On a separate, previously exposed Sweden–Switzerland 2022 gap (3900–4200 s),
the frozen cap screen withheld all 37 raw cap tracks and fusion left the
primary result at 1 TP, 0 FP, 0 FN, with correct colour, against one coarse
reference window. This is a limited cross-match false-positive check, not a
meaningful recall estimate for that production family.

The event detector is therefore still experimental. High temporal F1 on two
coarse windows does not support a full-video or game-state claim, and the
colour errors currently block reliable stone-state reconstruction. The later
follow-up below adds evidence, but does not establish full-video accuracy.

## Episode-colour and two-channel follow-up

An episode-colour rule fitted after the two 600–885 s mistakes keeps the
original event time but uses a nearby, substantially stronger opposite-colour
motion track to set stone colour. It retrospectively corrected both mistakes.
The next 900–1200 s source-only interval was frozen before running this rule.
It spans a first-to-second-end broadcast transition and has five coarse
agent-authored delivery windows. The frozen box/cap fusion plus colour rule
found 4 TP, 0 FP, 1 FN, all four colours correct (F1 0.889). It missed a red
throw around 1003 s because the learned-box track failed local-ice context
and the cap track fell just below the smooth-motion threshold. This first
failure is preserved in `china-third-live-transfer/`.

A second development rule then used agreement between these two raw tracks:
same colour, live overlay, motion in both tracks, strong cap local-ice context,
and at least eight aligned observations with median centres within 15 px.
When no accepted event lay within 20 s, it added the cap track as a
provisional event. This **postscore** change recovered the exposed miss,
giving 5/0/0 in that interval; it added nothing to the earlier China intervals.
After freezing the rule, it added no event on the previously exposed
Slovakia–USA G03 positive gap (which remained 2/0/0) and none in China's
source-only 0–290 s opening negative segment. The negative has no recall
denominator. A previously exposed Sweden–Switzerland gap also remained 1/0/0.
See `PAIR-TRANSFER-SELECTION.md` and preserved first transfer
artifacts. The two observation channels share colour segmentation and frames,
so agreement is corroboration, not independent validation. No full-recording
high-F1 or release-time claim follows from these small windows.
The prototype tests and Ruff checks pass with these experimental rules.

## Counter-concordance stress check on another match span

Before visual inference on Slovakia–USA 2022 at 2400–2700 s, the interval
and frozen model hashes were recorded in
`slovakia-counter-concordance/SELECTION.md`. A one-second counter audit was
readable in 293/300 seconds and found six stable decrements without unresolved
changes. A permissive counter-derived reference was frozen before reading
visual outputs. Because two ±15-second proxy windows overlap, a separate
one-to-one concordance scorer reports matches without calling them event F1.
The unchanged visual pipeline emitted seven candidates: six have temporal
counter matches, five also match colour, and one red cap candidate is
unmatched. The fitted colour rule flipped a true yellow delivery to red after
a different red stone moved near the house. This is a direct counterexample
to promoting that rule or the full visual fallback as a high-F1 detector.
The [first result and source audit](slovakia-counter-concordance/SELECTION.md)
are preserved. The next detector revision needs evidence that a stone came
from the delivery side before it reached the house, with view-aware identity
linking across camera cuts; motion strength alone is insufficient.
The [postscore camera-relative probe](slovakia-counter-concordance/SELECTION.md)
then compensated for camera pan/tilt. It separated a stationary house-stone
track from a moving delivered yellow stone, but a moving red shirt still
passed the relative-motion check. This confirms the next gate needs both
stone appearance and delivery-origin evidence; registration alone cannot
validate a throw. All prototype tests and Ruff checks pass after this probe.

## Side-view cap identity diagnostic

The public detection images inspected here are overhead views, whereas the
missed live-play stone can fill much more of a side-view frame. To test the
appearance gap, `sideview-patch-selection.json` fixed 12 Canada–China tracks
for development and 14 Slovakia–USA tracks for a cross-match probe. The
`sideview-patch-review-v1/` manifest links three sampled frames per track to
the source video hash, time, and cap box. Codex labeled the 78 crops from
contact sheets at the **sample** level; a track can switch from a player or
graphic to a stone. Two ambiguous crops were excluded. The reserved unseen
match was not touched.

`sideview-patch-transfer-v1/` stores a balanced linear SVM trained on the 35
unambiguous China crops. With its zero decision threshold fixed before the
Slovakia score, it classified 41 unambiguous Slovakia crops as 26 TP, 1 FP,
7 FN, 7 TN: patch precision 0.963, recall 0.788, F1 0.867. In particular,
it rejected some faces and graphics but missed real stones in crowded or
low-detail views. The selected crops, agent-authored labels, and tiny sample
make these **development diagnostics**, not independent object estimates or
throw-event scores. The verifier is not in the production pipeline: a strict
gate would sacrifice too much recall, and stone identity alone does not
identify which stone was delivered or whether it came from the delivery end.

Recreate the packet and frozen cross-match result with:

```sh
feasibility/scripts/python.sh prototype/scripts/build_cap_patch_review.py \
  --selection validation/curlobserver-learned-probe/sideview-patch-selection.json \
  --output /tmp/sideview-patch-review
# labels.json in the preserved review directory is the reviewed source of labels.
feasibility/scripts/python.sh prototype/scripts/score_cap_patch_transfer.py \
  --review validation/curlobserver-learned-probe/sideview-patch-review-v1 \
  --output /tmp/sideview-patch-transfer
```

The same China-only weights were then scored, without refitting, on 39
selected Sweden–Switzerland samples: 8 TP, 3 FP, 7 FN, 21 TN (precision
0.727, recall 0.533). `swiss-patch-review-v1/` contains the source-linked
sheet and labels; `swiss-patch-frozen-score.json` preserves the first score.
This third-match drop rules out promoting the first cross-match number as a
robust appearance estimate.

A fixed `C=0.1` balanced SVM and zero threshold were then used in three
leave-one-match-out development folds (`cap-patch-crossmatch-v1/`). With two
matches for training, the excluded-match patch F1 values were 0.941 on China,
0.935 on Slovakia, and 0.759 on Sweden–Switzerland. The pooled patch counts
were 64 TP, 3 FP, 11 FN, 37 TN. The Swiss miss includes a yellow stone over a
red rink marking; all three Swiss yellow scoreboard samples were false
positives. The exposed, handpicked material makes this a model-development
check, not a detector acceptance test.

Recreate the third-match and leave-one-match-out diagnostics with:

```sh
feasibility/scripts/python.sh prototype/scripts/evaluate_frozen_cap_patch.py \
  --review validation/curlobserver-learned-probe/swiss-patch-review-v1 \
  --source swiss-transfer \
  --model validation/curlobserver-learned-probe/sideview-patch-transfer-v1/model.npz \
  --output /tmp/swiss-patch-frozen-score.json
feasibility/scripts/python.sh prototype/scripts/cross_match_cap_patch_cv.py \
  --reviews validation/curlobserver-learned-probe/sideview-patch-review-v1 \
            validation/curlobserver-learned-probe/swiss-patch-review-v1 \
  --output /tmp/cap-patch-crossmatch
```

Camera-relative motion did not repair that case: the Swiss yellow-stone cap
track `G01-Y04` had zero reliable >5 px motion pairs, while a non-stone shirt
track `G01-R04` had three. `swiss-patch-camera-motion-v1.json` preserves the
pair-level result. Both examples reinforce that the missing event evidence is
**delivery origin and continuity** across the shot, with an explicit unknown
state when the broadcast does not show it. Appearance or motion alone cannot
confirm a throw. No experimental patch gate was added to the event pipeline.

## Shot continuity experiment

`candidate-sequence-review-v1/` now contains source-linked five-frame context
rows for 21 selected candidate tracks from China, Slovakia and
Sweden–Switzerland. These show the scene before track onset and afterward,
with observed boxes marked only when a track point is nearby. Several tracks
visibly switch between a person or rink graphic and a stone at an edit.
The packet is for developer review, not an independent event reference.

A conservative five-hertz hard-cut scan (mean grayscale change ≥45 and HSV
histogram distance ≥0.35) found 17, 19 and 19 edits in the three respective
300-second intervals. The cut audits found **17/65 Slovakia cap tracks,
10/47 China cap tracks, and 15/37 Swiss cap tracks** spanning at least one
detected edit. `scene_cuts.py` and the optional tracker cut boundary prevent
a within-shot track ID from crossing one of these edits. The preserved scans,
raw-track audits and cut-separated candidates are under each match's probe
directory. The scanner deliberately misses some subtle edits and says nothing
about whether adjacent shots show the same physical stone.

The old episode screen was replayed unchanged on the cut-separated cap tracks.
On the Slovakia 2400–2700 s interval, its candidate count rose from 3 to 7;
one-to-one **weak counter concordance** rose from 2 to 5 temporal matches and
from 1 to 2 colour matches against six decrements. Two cap candidates remained
unmatched, including the stationary-house candidate at 2440 s. Three matched
red cap candidates corresponded to yellow counter changes. This trade-off
does not justify adding cut splitting to accepted event output yet. The
counter reference has wide, overlapping windows and is not event F1.

The follow-on [broadcast-shot origin study](shot-origin-study.md) groups
motion by hard-cut shot and tests whether a throwing-side shot is followed
by same-colour stone motion. It removes several false player closeups but
still misses a clearly delivered red stone on a later frozen transfer.
The full target of independent, high-precision and high-recall throw-event
segmentation remains unmet.

Recreate the Slovakia cut audit in a fresh output directory by running
`scan_scene_cuts.py` on the source at 2400–2700 s, then
`audit_track_cuts.py` and `split_raw_tracks_at_cuts.py` with
`frozen-first-cap-raw.json` and the new cut scan. Pass the split artifact to
`screen_learned_gap_motion.py --large-cap-fallback`, then compare with
`score_counter_concordance.py` using
`frozen-counter-proxy-reference.json`. Each script records input/code hashes
and refuses to overwrite the preserved first result.
