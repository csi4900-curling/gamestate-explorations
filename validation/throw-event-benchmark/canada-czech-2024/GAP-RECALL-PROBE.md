# Displayed-end-2 accepted-event gap: receiving-only recall probe

The frozen full-match screen has a **248.067-second gap between accepted
candidate passages S39 (1402.6 s) and S42 (1650.7 s)**. This is an
accepted-event gap, **not a raw-candidate gap**. The early-ROI detector proposed
S40 (yellow, 1513.812 s) and S41 (red, 1590.967 s), and the fixed corridor
retained both. The [frozen screen](full-match-screen-postscore.json) abstained
on both because it found no supported receiving-motion path. Thus the initial
candidate stage did fire at the two source-visible motion windows; the
immediate recall problem here is the confirmation stage.

Source-only [10-second frames](gap-review/end2-1410-1640.jpg) and denser
[yellow-motion](gap-review/end2-1480-1530.jpg) and
[red-motion](gap-review/end2-1570-1610.jpg) contact sheets show stone-shaped
objects changing position during this gap. Those are agent observations from
sparse broadcast frames, not independent throw identities, releases, or an
exhaustive event list. Denser [S40 source frames](gap-review/s40-1512-1520-1s.jpg)
and [S41 source frames](gap-review/s41-1588-1602-1s.jpg), each with a JSON
source/frame-hash manifest, show a yellow stone traversing the left panel at
1512–1520 s and a red stone at 1588–1602 s. The
agreement in colour and approximate timing with S40/S41 is strong review
evidence, but the early-ROI object identity and exact event boundaries have
not been independently labelled.

The [original motion artifact](full-match-motion-merged-postscore.json)
explains the abstentions. For S40, a seven-sample left-view path splits after
a four-sample common prefix at 1518.5–1520.0 s; the selector marks it
`ambiguous_far_entry_motion_paths`. For S41, all 24 left-view frames register,
yet the coloured-stone proposer emits mostly static red locations during the
visible traverse, and the selector returns `no_supported_far_entry_motion_path`.
The [left-bound diagnostic](LEFT-BOUND-RECALL-DIAGNOSTIC.md) isolates a
specific proposal failure: the configured world bound clips the moving S41
stone before path selection. A separate [short-path development experiment](LEFT-SHORT-PATH-RESULTS.md)
accepted S40 with one of three positive stone patches, but did not recover
S41; that experiment did not change the 79-candidate frozen screen and does
not establish a recall gain on independent data.

To test a second candidate generator, a high-resolution scan sampled
**1480–1610 s at 0.5-second spacing** without using early-ROI trigger times.
The existing camera registration, coloured-stone proposals and 12-second
far-entry path selector were applied to sliding time windows for both colours:

| View scanned | Registered / total samples | Selected windows | Deduplicated path episodes | Source review |
| --- | ---: | ---: | ---: | --- |
| [Left](gap-review/left-receiver-1480-1610-postscore.json) | 261 / 261 | 0 | 0 | The current left calibration covers the near house and does not recover the source-visible distant motion in these windows. |
| [Right](gap-review/right-receiver-1480-1610-postscore.json) | 248 / 261 | 2 | 1 | [G01 frames](gap-review/right-receiver-path-frames/g01-path-review.jpg) show the path following a moving player's red-and-white hat at 1539.5–1541.5 s, not a stone. |

This is a **negative result for the present receiving-only generator**. A
registered camera and a long coloured motion path can still follow an athlete;
the current selectors also lose source-visible stone motion when proposals or
registration drop out and when the active receiving end changes. The scan
does not justify adding G01 to the event sequence. Its one episode remains
`physical_throw_verified: false` in the machine artifact.

The next recall experiment needs to preserve S40's stone-like shared prefix
without treating its later ambiguous branches as a verified trajectory, and
test expanded S41 proposal coverage on other recordings before changing the
frozen detector. It also needs to
choose the active receiving camera from video evidence and distinguish moving
athletes from stone bodies.

## S40 branch source review

The [1519.0–1521.5 s source-frame sheet](gap-review/s40-branch-source-review.jpg)
and [frame/hash manifest](gap-review/s40-branch-source-review.json) now isolate
the split. A yellow stone stays near `(395, 528)` pixels from 1518.0 through
1520.0 s while another yellow stone travels from `(506, 367)` at 1518.5 s to
`(488, 492)` at 1520.0 s. At 1520.5 s the proposer sees two yellow stones,
near `(367, 542)` and `(561, 516)`; both continue moving in opposite lateral
directions. This is consistent with a stone–stone contact or near-contact at
the house, which explains why a unique-path selector forks. The source
frames support **two visible moving stone bodies after the split**, not a
single unbroken identity assignment. The short-path branch selected the right
branch; it is a plausible continuation of the incoming stone, but that
identity requires frame-rate contact analysis to verify. Its last two patch
scores are negative, so the one-positive-of-three short-path acceptance must
remain a development proposal rather than a verified event trajectory.

This changes the next technical step: retain the pre-split incoming motion as
event evidence, then model contact as a branch with separate pre-existing and
incoming stone identities. A path selector that forces one continuous stone
through contact loses useful evidence and can misassign the post-contact
track. The existing 91-candidate development screen and frozen 79-candidate
screen are unchanged; neither count establishes event recall.

The [full ambiguous-prefix source review](AMBIGUOUS-PREFIX-REVIEW.md) extends
this check to all nine ambiguous rows and finds six distinct withheld
candidate windows with a visibly moving stone in the pre-split prefix.

Any resulting events still require source review and independent exhaustive
labels before they can support recall or F1. This exposed-match probe is not
independent validation, and neither frozen screen nor game-state timeline has
been changed by it.
