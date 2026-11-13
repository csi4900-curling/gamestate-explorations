# Czech panel-registration rule on Latvia end-six source paths

The Czech 2024 [split-panel rule](../canada-czech-2024/SPLIT-PANEL-REGISTRATION-CONTROLS.md)
was applied **unchanged** to the 1920×1080 Latvia end-six excerpt (source
seconds 5670–6670). Both [transfer artifacts](end6-split-panel-registration-czech-rule-transfer-development.json)
and [pre-movement controls](end6-split-panel-registration-held-path-controls-development.json)
pin the Czech code hash, Latvia source hash, input hashes, exact source times
and all short-frame registration decisions. The pixel paths come from the
earlier [source-reviewed 360p↔1080p correspondence](end6-cross-resolution-body-cap-development.json).
The 360p prefix centers were scaled by three into the right 960×1080 panel;
the panel was then resized without distortion to 640×720 for registration.
The source excerpt is decoded at `source_time_s - 5670`.

| Source-path group | Usable paths | Accepted 1 s pairs | Median residual | Residuals >5 px |
| --- | ---: | ---: | ---: | ---: |
| Source-reviewed moving-stone pixels | 16 | 40/40 | 53.886 px | 40/40 |
| Same high-resolution paths before the observed quiet-end boundary | 15 | 45/45 | 0.140 px | 0/45 |
| Source-reviewed person/clothing pixels | 1 of 4 with usable points | 0/2 | — | 0/0 accepted |

The held/quiet group uses at most the last four 1 Hz body-path points ending
**one second before** each source-reviewed quiet-end boundary. The first
moving path has no earlier body-path pair and is absent from that control
group. The remaining 15 high-resolution paths have no accepted pre-boundary
residual above 2.248 px. All 40 accepted moving-prefix residuals lie between
27.721 and 72.422 px. The only person/clothing proposal with a three-point
motion path abstained on both pairs because the proposed camera transform
conflicted with source-scene edges; the other three reviewed person proposals
have no usable onset path in this artifact.

This is a useful **cross-recording development transfer** of the registration
cue and an observed quiet-to-moving distinction on selected image paths. It
is not a physical throw-event precision/recall/F1 score. The same broadcast
style appears in both recordings, both were previously exposed to development,
the path classes and quiet boundaries came from same-agent source review, and
the held-path body association before motion is provisional. Raw path movement
also separates these selected groups, so these numbers alone do not prove
camera correction improves event detection over raw displacement. The source
video still needs an independent exhaustive throw reference, non-stone
negative paths with usable motion across diverse camera changes, and
persistent stone/board identity checks before a simulator-ready state can be
claimed.

## What this gives an onset segmenter

A simple first two consecutive >5 px rule applied to the *entire* 1080p
body path starts 10–15 seconds too early in three of the 16 paths: B003 red,
B009 red and B011 red have small earlier image-motion runs, then become
quiet again before the later throw-like motion. The existing
quiet-to-**directed**-motion rule uses three preceding quiet steps and two
strong downward steps. At the 640×720 panel scale, its pre-existing 360p
thresholds of 3/12 px/s become 6/24 px/s by geometry, with no Latvia-specific
rate fitting. The [cross-resolution onset artifact](end6-highres-body-onset-crosscheck-development.json)
finds an onset bracket for 15 of 16 reviewed moving-stone-pixel paths: **14
match** the source-reviewed 360p brackets exactly, and one starts its quiet
bracket one second earlier. The path beginning at the excerpt boundary has
too few earlier frames for the required quiet run. This is an observed image
onset bracket, never a measured physical release time. Both resolution lanes
come from the same match and were previously inspected, so this agreement is
a development consistency check, not independent onset accuracy.

The three red high-resolution paths left unmatched by the 360p moving-stone
correspondence are preserved in a [marked source contact sheet](end6-unmatched-highres-red-source.jpg)
with [frame and code provenance](end6-unmatched-highres-red-source.json).
The marked B005 pixels are red clothing; B006 and B007 follow faces/heads.
All three are too short for the quiet-to-directed-motion rule, so they receive
`insufficient_observations`, not a false event onset. This is a same-agent
source-pixel review, and it exposes a separate limitation: a high-resolution
red body/handle proposal can lock onto people even when its appearance score
is relatively strong. Timing abstention cannot replace a stone-versus-person
filter, and short true moving-stone paths can also lack a quiet prelude.

The [high-resolution underpoint audit](end6-highres-underpoint-context-development.json)
scales the older 360p ice-beneath-object band exactly 3× to 1080p and records
fractions for all 19 image paths. Its descriptive three-way tier marks all
16 selected moving-stone-pixel paths as clear; among the three visually
reviewed person paths, two are cluttered and one is ambiguous. The 0.05
clear/ambiguous boundary was selected after reviewing this recording. It is
therefore a review cue, not a validated hard veto or an independent transfer
score. The subsequent [unchanged-rule Czech 1080p transfer](../canada-czech-2024/CZECH-HIGHRES-UNDERPOINT-TRANSFER.md)
places 20/20 selected moving-stone-pixel prefixes in the clear tier and
23/23 selected person/equipment prefixes in the cluttered tier. Both sets
were source-reviewed by the detector developer and are not a complete event
reference; Czech samples use scaled cap centers rather than Latvia body
centers.

The [observed-segment ledger](end6-highres-observed-segments-development.json)
joins appearance tier, onset bracket, camera-relative moving-prefix residuals,
full source-pixel body path and any later partial-board observation status.
It preserves all 19 high-resolution paths: 15 have both a clear appearance
review tier and observed onset; one clear path begins moving at the excerpt
boundary and has no supported quiet prelude; three short person paths have
nonclear appearance and no onset. These are **review priorities** rather than
throw decisions. Same-agent source review selected the 16 matched moving
prefixes and their appearance samples, even though the class string does not
directly set a tier. Every row keeps release, settle, persistent identity,
metric trajectory, complete state and simulation readiness unverified.

Reproduce with `feasibility/scripts/python.sh
prototype/scripts/transfer_latvia_split_panel_registration.py` and then
`feasibility/scripts/python.sh
prototype/scripts/transfer_latvia_split_panel_quiet_controls.py` after moving
the existing outputs aside. The first runner verifies that the registration
code exactly matches the Czech edge-guard artifacts; the second verifies that
same code and the first Latvia transfer artifact.
Run `feasibility/scripts/python.sh
prototype/scripts/crosscheck_latvia_end6_highres_onsets.py` for the onset
comparison, followed by `feasibility/scripts/python.sh
prototype/scripts/render_latvia_end6_unmatched_highres_source.py` for the
marked unmatched-path packet, again preserving existing outputs first.
The appearance and joined ledgers are reproduced by
`feasibility/scripts/python.sh prototype/scripts/audit_latvia_end6_highres_underpoint.py`
and `feasibility/scripts/python.sh
prototype/scripts/export_latvia_end6_observed_segments.py` in that order.
