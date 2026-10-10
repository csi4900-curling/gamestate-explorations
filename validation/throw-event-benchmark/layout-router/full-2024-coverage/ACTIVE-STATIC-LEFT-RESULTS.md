# A split layout can hide a dead delivery camera

The [Latvia full-source transfer](LATVIA-SCOTLAND-RESULTS.md) reported only 72
accepted passages during six completed ends, yet the layout router called
6840/7059 seconds supported. Source inspection of its longest accepted-event
gap exposed a more basic failure: from about **5015 to 6670 s** the left panel
hardly changes, while the right panel continues showing live play. The
[sample sheet](latvia24-full-v1/long-accepted-gap-source-samples.jpg) shows the
same left image at 5300, 5600, 5900, 6200 and 6500 s; its right image and
scoreboard change. Neither the raw left-panel detector nor its accepted
timeline emits **any candidate** within those 1655 seconds. An apparent frozen
feed is plausible on Latvia, but the pixel audit alone cannot distinguish
that from another form of static source image.

We froze a simple **development image diagnostic** after this observation:
sample each 640×360 source every five seconds; compare consecutive frames in
the left 310×335-pixel panel; retain static-left runs of at least 60 seconds
when left mean absolute pixel difference is below 3; call a run *active on the
right* only when its median right-panel difference is at least 5. The
[source/code-hashed audit script](../../../../prototype/scripts/audit_split_panel_freeze.py)
records every pairwise measurement. The threshold was selected after the
Latvia failure was visible and is **not** a trained production router.

| Complete 2024 recording | Active static-left interval | Duration | Median left/right change | Raw left passages inside | Added detector-unsupported time |
| --- | --- | ---: | ---: | ---: | ---: |
| [Canada–Latvia](latvia24-full-v1/left-panel-freeze-audit.json) | 5015–6670 s | 1655 s | 1.63 / 12.73 | 0 | 1655 s |
| [Canada–Italy](new-preflight-italy24/left-panel-freeze-audit.json) | 2835–3200 s | 365 s | 1.24 / 16.34 | 0 | 365 s |
| [Canada–Scotland](scotland24-full-v1/left-panel-freeze-audit.json) | none | 0 | — | — | 0 |
| [Canada–China](new-preflight-china24/left-panel-freeze-audit.json) | none | 0 | — | — | 0 |
| [Canada–Estonia](new-preflight-estonia24/left-panel-freeze-audit.json) | none | 0 | — | — | 0 |

The [Italy source sheet](new-preflight-italy24/left-freeze-source-samples.jpg)
shows an **empty but apparently live** left camera during part of this interval,
while athletes and stones are in the right view. This is not necessarily a
frozen video feed; it has the same practical consequence for a left-motion
trigger. Static stretches in the three controls have low right-panel motion
too, consistent with titles, breaks or credits rather than this failure.

The [coverage overlay](../../../../prototype/source_activity_coverage.py)
preserves every original event and original unknown interval. It subtracts
only active static-left intervals from the router's supported split-view runs:

| Recording | Original supported / unknown | Revised supported / unknown | Newly flagged original events |
| --- | ---: | ---: | ---: |
| [Latvia](latvia24-full-v1/source-activity-coverage-overlay.json) | 6840 / 219 s | 5185 / 1874 s | 0 |
| [Italy](new-preflight-italy24/source-activity-coverage-overlay.json) | 8100 / 240 s | 7735 / 605 s | 0 |
| Scotland, China, Estonia | unchanged | unchanged | 0 |

The zero-event result is the failure signal, not reassurance: the original
router assumed that *recognizing the split layout* meant the delivery camera
was usable. It did not measure left-panel activity. The overlay makes missing
coverage honest; it does not recover or count physical throws. The next
detector needs an alternate trigger from the right view during such intervals,
followed by source-first complete-match scoring. Right-panel pixel change can
come from players and camera graphics, so it is not itself a throw event.
Any throws during those intervals are absent from the left-trigger candidate
set, and their number remains unknown without an independent reference.

The main `run_throw_pipeline.py` runner now exposes this same audit as an
opt-in `--audit-source-activity` sidecar for split-view runs. A fresh replay of
the complete 360p Latvia source with the interval-aware audit reproduces the
5015–6670 s active-static-left span and all four coverage totals above:
1655 newly unsupported seconds, 5185 supported seconds and 1874 unknown
seconds, with identical newly unsupported interval details. The separate
timeline and event candidates remain intact. The runner checks the audit and
overlay source, interval, input and code hashes before reusing them on resume.
The 1080p frame-normalization path has synthetic coverage tests but has not
been independently validated on a full high-resolution broadcast.
Its optional `--probe-blind-right` extension also replays the fixed 1 Hz
right-panel motion and early-entry triage inside those flagged spans. A fresh
Latvia replay from the newly generated coverage sidecar gives **131 raw right
tracks and the same eight entry IDs and crossing times** listed below, with no
change to the accepted left-trigger timeline. The source size remains 360p;
this is deterministic reproduction of an exposed development case, not a new
precision/recall result or a high-resolution transfer validation.
The [ordered runner replay](latvia24-full-v1/right-blind-runner-replay/latvia-candidate-review-union-current.json)
retains all **119 raw left proposals** (72 context-confirmed and 47 withheld)
and adds the eight right-only entry reviews, yielding **127 review candidates**.
Its six-stage saved chain includes the fresh activity audit, coverage overlay,
right motion, entry triage, camera-aware fusion, and ordered union; their
recorded input hashes were verified after preservation. None of the eight
right-only reviews becomes an accepted throw or a complete post-throw state.
The [bracket-aware partial-cap replay](latvia24-full-v1/right-blind-runner-replay/latvia-right-partial-caps-current.json)
samples each right-only entry at its interpolated line time and both observed
bracket endpoints. Five entries keep a locally matched partial colour-cap set
under all three anchors; R020 and R028 consistently abstain for scene/player
motion. **R025 changes from scene-motion abstention to a partial cap set within
its crossing-time bracket**, so the new output abstains as timing-sensitive.
An older partial-cap artifact used later right-entry times and reported six
usable sets and two scene abstentions. That difference is a direct warning
against treating a one-second timestamp choice as a settled-board fact.
The [current candidate-to-state handoff](latvia24-full-v1/right-blind-runner-replay/latvia-candidate-state-handoff-current.json)
joins this bracket-aware result to all 127 review candidates. Its 119 left
proposals are marked unsampled by this right-only board stage; five right
entries carry partial image-cap sets, two scene abstentions and one
timing-sensitive abstention. It does not import the older six/two board
judgments or their adjacent-cap transitions. Every candidate still has
unknown physical shot identity and complete board, with simulation readiness
false.
The current runner replay also pins observed motion spans for all 119 raw
left proposals and all eight right-only prefixes. Median spans are **1.2 s**
for left proposals and **4.0 s** for the right-entry prefixes. They delimit
the pixels supporting each proposal; they do not mark physical release,
arrival or settle boundaries.

The later source-reviewed terminal-cut overlay and this source-activity audit
now meet in an additive candidate handoff: [Italy](../../canada-italy/right-large-cap-full-candidate-pre-post-image-state-handoff-left-trigger-coverage.json)
retains 139 candidate rows and separately marks **365 s of left-trigger blind
coverage** inside its supported split-view layout; [Estonia](../../canada-estonia-2024/right-large-cap-full-candidate-pre-post-image-state-handoff-left-trigger-coverage.json)
retains 156 rows and has no active static-left interval under the same sampled
rule. The one Italy right-only candidate in the blind interval, `R01:A128` at
3197.206 s, was [source-reviewed as a person/equipment path](../../canada-italy/right-large-cap-full-r01-disagreement-source-review/source-prefix-classes.json).
It is retained as a review proposal, not a rescued throw. The handoffs keep
layout support and left-trigger support distinct; neither establishes how many
physical throws the left trigger missed during the blind interval.

A subsequent [lower-ice source-frame diagnostic](LEFT-BLIND-ICE-ACTIVITY-RESULTS.md)
finds 0/66 active five-second pairs in the interior of Italy's blind interval,
versus 50/324 in Latvia's. The threshold was selected after viewing both
recordings. Later [Latvia spike source strips](../../canada-latvia-2024/left-blind-lower-ice-spike-source-sheets/manifest.json)
show many foreground athletes/wheelchairs, so the cue is useful only for
directing review, not for counting or directly detecting throws.

## First right-view motion probe

To test whether an alternate trigger can at least surface objects in these
blind spans, a [fixed 1 Hz colour-motion probe](../../../../prototype/scripts/probe_static_left_right_cap_motion.py)
searched the right-panel rink image only. It used small red/yellow contours in
source pixels x=330–630, y=145–325 and the pre-existing short-track rule
(four observations, three seconds, 25 px span). The source/overlay/code-hashed
outputs contain **131 raw moving tracks** in
[Latvia](latvia24-full-v1/right-motion-in-static-left.json) and **nine** in
[Italy](new-preflight-italy24/right-motion-in-static-left.json). Neither count
is a count of deliveries; greedy tracking can follow parked stones, shirts,
wheelchairs, brooms or switch objects.

A deliberately simple *post-probe review selection* required a track to start
at y≥250, move at least 70 px upward overall, and last at most 60 seconds.
It selected eight Latvia tracks and none in Italy. The
[source contact sheets](latvia24-full-v1/right-static-track-review/manifest.json)
show first, middle and last tracked pixels. At least the early trajectories
[R005, R008, R014 and R017](latvia24-full-v1/right-static-track-review/sheet-01.jpg)
and [R020 and R028](latvia24-full-v1/right-static-track-review/sheet-02.jpg)
show moving stones in sampled right-view frames. R025 begins on a visible
yellow stone but appears to drift to nearby equipment/person pixels, while
R081 follows a red-clad player. This is agent inspection of prediction-selected
frames, **not independent event labels or proof that each path is one physical
throw**. The [Italy selection manifest](new-preflight-italy24/right-static-track-review/manifest.json)
records zero tracks under the same post-probe rule; it does not establish that
Italy's 365-second interval was throw-free.

This probe establishes a plausible right-view recall channel during Latvia's
left-panel failure and immediately exposes a false-positive/identity problem.
The next stage must distinguish delivered stones from other right-panel motion,
handle camera edits and validate complete event windows on a source-first
reference. None of these right-view tracks enters an accepted event timeline.

### Early right-view entry tier

After inspecting those raw tracks, a separate **post-review development tier**
tests a short moving prefix rather than treating each greedy track as one
physical identity. Its [rule](../../../../prototype/right_view_entry_triage.py)
requires the first coloured blob to appear at y≥250 with area ≥12 px² and a
nonvertical box, then reach y≤220 with at least 60 px upward displacement
within 20 s. It timestamps the y=250 crossing between observed one-second
samples and retains only the prefix through confirmation. The threshold
choices followed source inspection; this is not a frozen cross-recording test.

The [Latvia triage](latvia24-full-v1/right-entry-review-triage.json) preserves
all **131** raw track IDs and promotes **eight** to an *entry review* tier:
R005, R008, R014, R017, R020, R024, R025 and R028. Their early-line
timestamps are 5066.739, 5118.694, 5189.300, 5255.212, 5311.684,
5377.750, 5442.708 and 5565.263 s. The
[first four](latvia24-full-v1/right-entry-review/sheet-01.jpg) and
[next four](latvia24-full-v1/right-entry-review/sheet-02.jpg) source strips
show a moving coloured stone at the first, early-line and confirming points
of **each short prefix**. R024 is a stone-led red prefix missed by the earlier
full-track-duration review rule. The previously selected R081 player track is
excluded because its initial red patch is too small and vertically shaped.
The later object switch on R025 remains a warning against extending the
prefix into a full-throw trajectory. The [source-strip manifest](latvia24-full-v1/right-entry-review/manifest.json)
pins all eight source framesets and input hashes.

The same tier produced **zero** entries from Italy's nine raw right tracks;
its [triage artifact](new-preflight-italy24/right-entry-review-triage.json)
keeps all nine available for other review strategies. Eight visually
stone-led prefixes do **not** prove eight distinct delivered throws, complete
event boundaries, or recall over the remaining ~1100 seconds of Latvia's blind
interval. No candidate is auto-accepted into the match timeline, and event F1
remains unknown.

The later [expanded right-extractor transfer](EXPANDED-RIGHT-ENTRY-TRANSFER-RESULTS.md)
replays the entire 5015–6670 s Latvia blind interval with a wider near-camera
ROI and larger colour-contour allowance. It retains the same eight early
entry reviews at identical crossing times and adds none, despite two extra
raw colour tracks. All eight remain short moving-stone paths in selected
source strips. The widened extraction alone therefore does not resolve
unknown throw recall in the rest of this left-blind interval.

### Later right-panel motion check

The absence of further early-entry proposals is worth investigating, but it
does not justify promoting every later coloured track. A source-frame review
of six yellow raw tracks from **5627–6584 s** is saved in the
[late-track source strips](latvia24-full-v1/late-right-motion-source-review/manifest.json).
These tracks begin around right-panel y=201–208, below the early-entry tier's
required y≥250 start. Their marked positions subsequently move **toward larger
image y** (toward the camera) or remain in the foreground, rather than showing
the required upward passage into the house. Several strips show a person
handling a stone at the track's first frame, with wheelchairs and players
intervening later. This is consistent with stone return or repositioning after
play; the sampled frames cannot prove the complete activity or rule out a
delivery elsewhere in the interval. The six tracks therefore remain raw
motion evidence, not recovered throws. This audit exposes a concrete source
of false positives for a wider right-view motion trigger, while the late
blind interval remains unscored against an independent reference.

The review renderer now accepts explicit `--track-ids` for such diagnostic
source strips. Its default threshold-selected output is unchanged, and the
manifest records requested IDs plus video, probe and renderer hashes.

Reproduce the source audit and overlay, using different output paths to keep
these first artifacts intact:

```sh
python prototype/scripts/audit_split_panel_freeze.py \
  --video validation/throw-event-benchmark/canada-latvia-2024/source-360p.mp4 \
  --output /tmp/latvia-static-left.json
python prototype/scripts/overlay_source_activity_coverage.py \
  --timeline validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1/timeline.json \
  --activity-audit /tmp/latvia-static-left.json \
  --output /tmp/latvia-activity-coverage.json
```
