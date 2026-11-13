# Latvia end-6 high-resolution source check

The [1080p source excerpt](../../canada-latvia-2024/source-1080p-5670-6670.mp4)
covers source time 5670–6670 s. It was downloaded from the same YouTube source
(`YCfdKLu-BRc`, video format 137) with `yt-dlp --download-sections
'*01:34:30-01:51:10'`; its SHA-256 is
`481542262453e8fc8cce3632736550aa70b9e22702134010a0c4d04cb43bed32`.
The clip is 1920×1080 at 30 fps. The previously pinned full source is 640×360.

At source times 5902, 6332 and 6552 s, the 1080p excerpt sampled at
`t - 5670` aligns with the full 360p recording: mean absolute differences
after downscaling are 6.0, 5.7 and 5.6 pixel values, respectively. A
±0.2-second shift made each comparison worse. The [comparison sheet](../../canada-latvia-2024/end6-highres-selected-comparison.jpg)
shows the same right-ice crop at native 1080p alongside the corresponding
360p crop enlarged threefold. These times were selected after examining the
360p failure and are diagnostic examples, not validation samples.

The larger source makes the grey stone bodies, handles and wheelchairs easier
to distinguish. In all three shown frames, however, the foreground player
and wheelchair still overlap the candidate stone region. The visible stones
could be stationary or being handled; a single sharp frame does not show a
delivered-stone path or a board transition. Higher resolution is useful for
a future body-and-handle tracker, but this check has not recovered a late
throw, measured spin, or made the physical game state simulation-ready.

A subsequent [one-second native-resolution colour scan](latvia24-full-v1/end6-highres-cap-transfer-development.json)
covered all 1,000 seconds of the excerpt. Unlike the existing patch classifier,
it processes the colour mask at 1080p and normalizes candidate positions back
to 360p coordinates for comparison. It found 151 red and 23 yellow lower-ice
colour proposals; 83 red and one yellow proposal had no same-colour 360p
proposal within five normalized pixels at the same second. The greedy image
linker retained 19 red downward, five red upward and seven yellow downward
paths. These counts are proposal coverage, not object recall or throw recall.

The [source sheet for all five upward paths](latvia24-full-v1/end6-highres-upward-source-review.jpg)
and its [review manifest](latvia24-full-v1/end6-highres-upward-source-review.json)
show that the tracked pixels belong to players, a broom or wheelchair details
at the selected first/middle/last times. This same-agent review does not prove
the full interval throw-free; it shows that the new upward colour paths do not
verify a delivery. A useful next experiment needs a stone-body observation
and temporal separation from the athlete, not a looser cap threshold alone.

## Grey-body and handle development probe

A [second 1080p probe](latvia24-full-v1/end6-highres-body-template-development.json)
uses an 80×37-pixel grey-body crop from a source-visible moving yellow stone
at **2310 s** in an earlier excerpt of the same Latvia match. Grayscale
template matching at half resolution follows that stone over seven successive
one-second samples, 2309–2315 s, with best-match scores 0.59–0.91. This is a
positive development control from one selected path, not a trained or
independently validated detector. The template, search region, thresholds,
source hashes and every proposal are in the ledger and reproducible runner.

Across 5670–6670 s, the body probe yields 289 image proposals and ten
linked paths with at least three samples and 75 px vertical span: nine
downward and one upward. The only upward path, B006 at 6229–6232 s, is
visibly the back of a moving wheelchair, not a stone. Body shape plus upward
image motion therefore still produces a false throw candidate.

The [handle-colour screen](latvia24-full-v1/end6-highres-body-handle-screen-development.json)
checks an 84×47-pixel region immediately above every body proposal. It keeps
all seven positive-control observations and rejects all four B006 wheelchair
observations. It keeps 258 of the 289 blind-interval body proposals and leaves
eight linked downward paths, **zero linked upward paths** under this
development rule. The [paired source sheet](latvia24-full-v1/end6-highres-body-handle-source-review.jpg)
and [review manifest](latvia24-full-v1/end6-highres-body-handle-source-review.json)
show the moving-stone and wheelchair examples. This threshold was chosen
after seeing those examples; it is not a held-out result, and a hidden handle
could cause a missed throw. None of these counts proves the blind interval
throw-free or estimates event precision/recall. Body, handle, player context
and view changes still need joint validation on independently labelled video.

The [full 1,110-second transfer on the earlier 1080p excerpt](LATVIA-EARLY-HIGHRES-BODY-TRANSFER.md)
shows that this single yellow-stone template follows five visible moving
yellow stones but misses source-visible red moving stones. The colour gap
prevents promoting this development cue to the match detector.

The red template developed on those earlier source-visible shots was then
frozen and transferred to **every second of the 5670–6670-s blind interval**.
The [late red ledger](latvia24-full-v1/end6-highres-red-full-transfer-development.json)
verifies 14 nonoverlapping, source-hashed shards. It records 1214 grey-body
proposals and 474 red-handle-supported boxes. Temporal linking retains 11
downward image paths and **no upward path**. The earlier yellow body/handle
pass retained eight downward and no upward path on the same 1080p source.
This two-colour result does not recover a new throw candidate under the
frozen body/handle motion rule. It is not evidence that no throws happened:
one-second sampling, occlusion, camera coverage, the hand-picked templates
and still-unverified end timing can all prevent a true delivery from forming
an upward path. Independent complete-interval labels remain necessary to
determine recall and whether this interval is actually throw-free.

This explicit noncoverage result is also carried in the
[full-match receiving-motion handoff](LATVIA-RECEIVING-MOTION-HANDOFF.md).
