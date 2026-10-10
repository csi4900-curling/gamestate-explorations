# Canada–Latvia full-match candidate and partial-state handoff

The [ordered machine-readable handoff](latvia24-full-v1/full-match-candidate-partial-state-handoff.json)
joins the frozen full-match left timeline, all of its raw screen abstentions,
the static-left right-entry proposals, source-activity coverage, and the
alignment-gated partial-cap sequence. The [exporter](../../../../prototype/scripts/export_latvia_full_candidate_handoff.py)
checks source and intermediate artifact hashes before writing the result.

| Observation tier | Rows | Meaning |
| --- | ---: | --- |
| Left screened passage | 72 | Provisional image-motion event, not verified physical delivery |
| Left raw screen abstention | 47 | Preserved for false-positive/false-negative review, not counted as an event |
| Right-only entry during static-left coverage | 8 | Short colour-cap motion prefix, review only |
| **Ordered observations** | **127** | Distinct evidence rows, **not 127 throws** |

The 72 screened left passages plus eight right-only reviews make **80 possible
event proposals** in this combined handoff. That is not a physical throw count
or a recall estimate; some left proposals may be false, and the right proposal
stage can miss deliveries. The official six completed ends imply 96 nominal
deliveries, but the book does not timestamp or match them to these rows. The
handoff retains the explicit source-time gaps `[0,90)` and `[6930,7059)` and
the separate left-trigger blind interval `[5015,6670)`.

A [source-pixel review ledger](latvia24-full-v1/source-pixel-review-ledger.json)
now attaches seven earlier prediction-targeted crop judgments without altering
the screen: four tracked crossings show a stone body, and three show person
pixels. **S45 is one of the 72 screened passages yet visibly follows a
player**; S10 and S72 were already withheld. The [marked source crops](latvia24-full-v1/highest-comovement-crossing-crops/sheet-01.jpg)
and [withheld crops](latvia24-full-v1/isolated-withheld-crossing-crops/sheet-01.jpg)
support those local image classes. A stone body at one crossing still does not
verify a delivered stone. The ledger was selected and judged by the detector
developer, not an independent validator; the other 120 rows remain unreviewed
at this level.

Six of the eight right-only entries carry repeated **image-cap proposals**;
two abstain amid scene/player motion. Four adjacent pairs have guarded local
cap associations, while three adjacent comparisons abstain. Those attached
observations are partial right-camera pixels, not a settled board, score,
metric rink state, or persistent stone identity. Every row explicitly leaves
physical release, settle, end/official shot identity, full trajectory, spin,
complete board and simulation readiness unknown. The eight right entries are
retained once each; their right-camera prefixes and cap observations are
attached to the same ordered rows rather than double-counted as new throws.

This artifact is a **reproducible candidate-to-state handoff**, not validated
video-to-game-state reconstruction. It makes the remaining work testable:
source-first independent throw labels for event precision/recall, a stone
detector and camera-direction model for the late blind interval, physical
cross-view identity, calibrated trajectories, and complete post-throw board
observations before simulation or coaching claims.

A later [full-match area-aware union](../../canada-latvia-2024/FULL-MATCH-AREA-CANDIDATE-UNION.md) adds 20 source-reviewed right-only paths from the later part of the same left-static interval. It preserves this original 127-row artifact and all abstentions rather than rewriting the first handoff.

The [full-match evidence explorer](../../canada-latvia-2024/full-match-review/index.html)
makes the 127 rows navigable against the pinned source video, including the
left-trigger blind interval and the partial right-camera cap evidence. It
also visibly marks the three reviewed person paths, including screened S45.
It exposes predictions and is separate from independent labeling.

The [broadcast-display sidecar](latvia24-full-v1/full-candidate-display-context-development.json)
now attaches repeated scoreboard run context to all 127 rows without changing
the handoff. In displayed run 6 it finds just one accepted left passage,
three withheld left motions and no right-only proposal; the static-left
interval covers its first 1000 s. This identifies a focused coverage audit,
not a verified per-end delivery count. The geometry and source checks are
documented in the [2D marker report](2D-MARKER-CANDIDATE-CONTEXT.md).
