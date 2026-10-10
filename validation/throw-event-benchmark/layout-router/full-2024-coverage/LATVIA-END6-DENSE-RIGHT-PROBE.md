# Latvia displayed end 6: dense right lower-ice probe

The [full candidate/display join](latvia24-full-v1/full-candidate-display-context-development.json)
contains no right-only entry proposal during displayed run 6. Its first
1000 seconds, **5670–6670 s**, overlap the source-observed static-left interval,
so the right view is the only active delivery-camera candidate channel there.
The prior [late right-track review](LATVIA-LATE-RIGHT-TRACK-FAILURE.md) found
that simply loosening the crossing line would mostly promote handled or parked
stones.

A new [reproducible 0.5-second scan](latvia24-full-v1/end6-lower-cap-direction-development.json)
uses the unchanged right-panel colour contour generator on all **2001** source
frames in that interval. It keeps proposals with centres at image y ≥ 235 px
and links nearby same-colour pixels only for an image-motion diagnostic. It
finds **176 red and 48 yellow lower-ice colour proposals**. Under its declared
three-sample, ≥20 px vertical-change rule, 25 linked image paths move
downward and four move upward; all four upward paths are red. These are
colour-image paths, not stone identities.

The [marked source frames](latvia24-full-v1/end6-upward-colour-source-review.jpg)
show all four upward paths, D019, D020, D021 and D028, on **players' clothing**
at the tracked pixels. The [review manifest](latvia24-full-v1/end6-upward-colour-source-review.json)
records those same-agent judgments and hashes the source, probe, runner and
image. No new physical throw or right-only event is added to the candidate
ledger.

This isolates a failure of the colour-motion proposal channel: finer temporal
sampling exposes motion, but the surviving upward paths in this review are
player pixels. It does **not** prove there were no deliveries in the interval.
The camera may hide a small cap, a stone can be occluded by a player, and a
transit can occur between half-second samples or outside y ≥ 235. The next
recovery step needs a stone-body/ice observation and camera-aware short path,
then source checks of candidates and misses. It cannot rely on red/yellow
motion direction alone. Independent complete-interval labels are still needed
to measure throw precision, recall and F1.

A [periodic receiving-house observation scan](LATVIA-END6-PERIODIC-BOARD.md)
now covers the same interval independently of right-entry triggers. It yields
partial image-cap states and reviewable differences, but foreground overlap
prevents those differences from being promoted to physical throws or boards.

## Later area-aware full-source transfer

The unchanged Canada–USA-developed [area-aware full-source transfer](../../canada-latvia-2024/FULL-RIGHT-AREA-TRANSFER-RESULTS.md) subsequently recovered 20 right-only proposals in this same interval. Marked source-frame review found moving stone pixels in 16 and people/clothing in four. Thus the older lower-ice probe's absence of a surviving stone path was a **proposal-method failure**, not evidence that the interval lacked deliveries. The 16 source-visible paths remain unverified as physical throws; the later result does not revise this probe's original output or supply independent recall.
