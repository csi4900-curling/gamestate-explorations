# Full-match corridor-withheld candidate audit

The frozen first-stage corridor withholds **31 of 147** raw early-ROI motion
spans. This postscore audit ran the same 1080p, 0.5-second / 12-second
receiving-motion scan on **all 31 withheld IDs**, using the same source and
preselected right-camera anchor at 6525 s. It did not alter the frozen screen
or use a label to select which withheld ID to process.

| Evidence stage | Withheld IDs |
| --- | ---: |
| Raw spans outside the corridor | 31 |
| No supported unique receiving path | 25 |
| Supported candidate-local receiving path | 6 |
| At least one positive learned patch among three path samples | 4 |
| Distinct patch-positive paths after timed-path deduplication | 2 |

The six supported path IDs are **S05, S26, S74, S93, S94, S95**. S05 and S26
failed the unchanged appearance rule. S93–S95 have seven identical timed path
observations and therefore represent one path proposal, not three distinct
stone movements. The remaining distinct proposals are S74 and S93.

High-resolution source frames show the four distinct paths tracking people:

| Path | Source-visible tracked object | Patch result |
| --- | --- | --- |
| [S05](off-corridor-source-review/s05-path-review.jpg) | Red clothing and hat on a moving player | 0/3 accepted |
| [S26](off-corridor-source-review/s26-path-review.jpg) | Red jersey print on a moving Canadian player | 0/3 accepted |
| [S74](off-corridor-source-review/s74-path-review.jpg) | Red jersey print on a moving Canadian player | 1/3 accepted |
| [S93](off-corridor-source-review/s93-path-review.jpg) (also S94–S95) | Wheelchair footrest or shoes | 2/3 accepted |

These are **agent source reviews of false-positive paths**, not independent
ground-truth labels. The one-of-three patch rule accepted the jersey once and
the footrest twice. This is a concrete reason to retain the ice-corridor
filter in the current screen rather than simply forwarding all raw spans.
The [cross-corridor overlap audit](cross-corridor-motion-overlap-postscore.json)
also shows that the withheld footrest path S93–S95 reappears as **accepted
S96**, which the corridor alone did not prevent. The [S96 source review](source-review/s96-review.json)
records that second accepted false-positive path separately from the frozen
79-candidate screen.

The complete [source-only still packet](off-corridor-source-review/manifest.json)
contains two full-video frames for every withheld ID. It helps inspect context
but cannot establish exhaustive throw recall. A missing path can reflect a
weak detector, occlusion, or camera geometry; it does not prove there was no
delivery. A true recall/F1 assessment still requires continuous, independent
source-video annotation, including deliveries that created **no** raw span.

Reproduce the diagnostic from the pinned
[withheld input](off-corridor-motion-input-postscore.json),
[31-shard scan](off-corridor-motion-partitions/),
[hash-checked merge](off-corridor-motion-fixed-grid-postscore.json),
[patch audit](off-corridor-patch-postscore.json),
[raw patch screen](off-corridor-screen-raw-postscore.json), and
[timed-path deduplication](off-corridor-dedup-postscore.json). The renderer
[manifest](off-corridor-source-review/path-review-manifest.json) pins the source
and motion artifact hashes used for the four high-resolution source reviews.
The involved scripts are
`prototype/scripts/build_corridor_withheld_motion_input.py`,
`prototype/scripts/build_off_corridor_review.py`, and
`prototype/scripts/render_off_corridor_path_review.py`.
