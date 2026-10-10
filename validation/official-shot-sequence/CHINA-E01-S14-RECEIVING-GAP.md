# China end-one receiving-view recall lead

The [v3 sequence review queue](pwg2022-v3-sequence-review-queue-development.json)
places no candidate at official shot E01-S14 between `VISUAL-S58` and
`VISUAL-S66`. This official slot is a **postscore selection cue**, not a video
label or runtime detector input. The official list calls E01-S14 a red China
take-out, which is compatible with, but does not identify, the red travel seen
in the source footage.

The broadcast shows the China delivery setup in S63, cuts to a close-up, and
then cuts at 915.4 s to S64, where a red stone travels toward the house.
The physical release is not shown continuously. [Before-cut frames](china-s63-e01-s14-gap-source-review.jpg)
and [receiving-view frames](china-s64-s65-e01-s14-gap-source-review.jpg)
make the visual evidence inspectable.

The [reproducible diagnostic](china-e01-s14-receiving-gap-development.json)
records the current pipeline's failure here:

- The origin model calls S63 an origin shot, but the full-source held-to-motion
  scanner finds no raw passage in S63 or S64.
- The verified 915.4 s cut is followed by two legacy red-cap track summaries
  in S64. Their paths are not enough to establish one persistent physical stone.
- The stricter post-cut scanner accepts **zero red or yellow tracks** in
  915.6–927.4 s, despite visible red travel. A camera-following view, gaps in
  cap detections, and track association each need diagnosis before a rescue
  rule can be promoted.

This is a selected development recall lead. It does not establish physical
throw-event recall, an exact release time, or identity across views. It shows
why a detector that requires a visible origin release or a sustained
image-space cap track can miss a broadcast throw when the release is obscured
and only receiving-view travel remains.

Reproduce the diagnostic and source sheets from the project root:

```sh
feasibility/scripts/python.sh prototype/scripts/audit_china_e01_s14_receiving_gap.py
feasibility/scripts/python.sh prototype/scripts/render_china_e01_s14_gap_source_sheets.py
```
