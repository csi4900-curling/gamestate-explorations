# Throw-event measurement gate — 7 October 2026

The target is **high precision and high recall**, not a large raw event count.
The [public-reference audit](PUBLIC-REFERENCE-AUDIT.md) checks available
curling annotations. The 112 CurlObserver throw-to-stop clips can test stone
tracking but cannot measure full-match event F1 because their enclosing match
timelines and quiet intervals are absent.
The later [right-cap tail transfer](RIGHT-COLOUR-TAIL-TRANSFER.md) checks one-frame pixel continuation on Italy and Estonia. It extends observed-pixel evidence but also follows person-associated colour in two reviewed paths, so it is not an event-acceptance filter or a new F1 result.
The [two-stage development audit](../two-stage-throw-audit/index.html) now
preserves every raw 2024 proposal when an existing confirmation gate withholds
it. The runnable split-screen adapter writes `triage.json` beside its frozen
`events.json`: the former contains the complete proposal/review ledger, while
the latter remains the automated candidate set used for scoring. This does
not improve a frozen score or establish independent full-match accuracy.
The `prototype/scripts/run_two_stage_filter.py` development runner applies the
same 2024 image-context gate to raw virtual-line or motion-span proposals and
retains every withheld proposal for review. Its China/Estonia rechecks are
post-score diagnostics; the USA output reproduces the frozen first score.
This directory establishes the scoring contract before the next detector version.
The provisional acceptance bar is at least **0.95 precision and 0.95 recall**
on complete, continuous recordings, with zero added timing tolerance beyond
each frozen delivery window. This is a gate for each recording, not evidence
that one passing recording generalizes. Diverse held-out broadcast families and
quiet intervals must be included. We will report F1 as well, but a high F1
cannot compensate for one weak component. `prototype/event_acceptance.py`
implements the per-recording gate and refuses partial timelines or a
non-independent reference. Publisher or other external event labels can qualify
if their source, exhaustive coverage and independence are verified; the user
does not have to create labels for development.
Run `scripts/score_throw_events.py --assess-target --source-video /path/to/full-source.mp4`
with the usual reference, prediction and output arguments to record this
decision alongside the raw score. The scorer measures the supplied file's
SHA-256 and `ffprobe` duration and requires them to agree with the declared
source hash and duration (within 0.1 s for duration). A declared excerpt
duration alone cannot establish complete-source scope. The strict gate also
requires `coverage_gaps_s: []` and
`coverage_verified: true` in predictions, `exhaustive: true` in the reference,
matching source hashes, a shared `source_duration_s` with the reference's
`source_duration_verified: true`, and `source_interval_s: [0, source_duration_s]`
in both files. A matching excerpt cannot pass by declaring that excerpt
"complete." It also requires `reference_method: human_independent` or
`publisher_independent`. These declarations require evidence; the current
partial timelines cannot meet them.

An experimental [layout preflight and adapter runner](layout-router/README.md)
now dispatches between the two known production families and returns unknown
for mixed or unsupported sampled layouts. Its six-source routing check is
in-sample; it is not an additional event-F1 validation.
Full-source passes now retain partial timelines with explicit gaps. On the
Beijing 2022 Canada–China recording, source review found a real yellow throw
inside a 300-second interior layout gap. A visual gap probe records it as an
unconfirmed candidate. This demonstrates a live-play recall failure that
the earlier 18.5-minute F1 window did not measure.

## What one event means

A throw event is an actual delivered stone travelling from the departure area
toward the playing end. Its detected timestamp may be an observed line crossing;
release time remains separately unknown. A moving player, broom, displaced stone,
practice movement or camera cut must not become a confirmed throw merely because
it moves in the same image direction. Uncertain cases may be retained as explicit
candidates, but they do not count as correct confirmed events.

The reference for each recording must cover a declared continuous interval,
including all visible deliveries and quiet periods. Every predicted event in that
interval is scored one-to-one against a reference delivery interval. Unmatched
predictions are false positives; unmatched deliveries are false negatives. Colour
errors are reported separately after temporal matching. Empty videos/intervals
must be included to test false events. A tolerance, if used, is fixed before
looking at predictions. The default is zero beyond the labelled interval.

`throw_event_benchmark.py` reports TP, FP, FN, precision, recall, F1, colour errors,
and a separately optimized colour-aware precision/recall/F1. A wrong-colour
temporal match counts as a false positive and false negative in the colour-aware
score. The scorer checks non-overlapping references, timestamps and unique IDs.
It does not infer exact release accuracy or validate the labels.

## Current measured status

| Recording | Reference | TP / FP / FN | F1 | Interpretation |
| --- | --- | --- | --- | --- |
| Canada–Korea 2024, one end | AI-reviewed gate intervals on the same end used to develop the detector | 16 / 0 / 0 | 1.00 | Development score only; no generalization claim |
| Canada–Slovakia 2024, fixed 18.5-minute interval | No exhaustive event reference; retrospective AI review found at least two player-head events among 15 proposals | Not computable | Unknown | Transfer failure demonstrated; recall unmeasured |
| Canada–Italy 2024, fixed 18.5-minute interval | Agent-blind 5-second source sheets, frozen before inference; 17 coarse delivery windows | 15 / 1 / 2 | 0.909 | First transfer score, below target; sparse-sheet reference may be incomplete |
| Canada–China 2024, fixed 18.5-minute interval | Agent-blind source sheets frozen before inference; 18 coarse delivery windows | 17 / 4 / 1 | 0.872 | First bidirectional plus corridor transfer score; precision 0.810, recall 0.944, below target |
| Canada–Estonia 2024, fixed 18.5-minute interval | Agent-blind 5-second source sheets frozen before inference; 17 coarse delivery windows | 13 / 0 / 4 | 0.867 | First frozen multi-gate plus motion confirmation transfer; recall 0.765, below target |
| Canada–China 2024, second hash-selected five-minute window | Source-first one-second sheets and seven coarse windows, frozen before opening saved full-timeline predictions | 7 / 0 / 0 | 1.000 | Same-agent development agreement only; release timing, completeness and full-recording F1 unproven |
| Canada–Estonia 2024, second hash-selected five-minute window | Same source-first protocol, six frozen coarse windows | 6 / 0 / 0 | 1.000 | Same-agent development agreement only; no independent or cross-family claim |
| Canada–USA 2024, fixed 18.5-minute interval | Agent-blind source-only sheets frozen before inference; 20 coarse delivery windows | 19 / 1 / 1 | 0.950 | First span-context transfer; precision and recall 0.950, with one event 0.552 s before a coarse window |
| Canada–China 2022 Paralympics, fixed 18.5-minute interval | Agent-blind source sheets prepared before inference; 20 coarse delivery windows across two ends | 0 / 0 / 20 | 0.000 | Different camera family: fixed split-screen gate has no coverage |
| Sweden–Switzerland 2022 Paralympics, fixed 18.5-minute interval | 19 agent-blind coarse windows frozen before first inference | 17 / 0 / 2 | 0.944 | First pass of Beijing overlay plus visual fallback; recall below target |
| Slovakia–USA 2022 Paralympics, fixed 18.5-minute interval | Source-only sheets inspected, but no exhaustive reference could be established | Not computable | Unknown | Frozen revised candidate emitted 16 events; coverage probe only |
| Canada–Norway 2022 Paralympics, full match | Official numbered-shot pages, no video timestamps | Not computable | Unknown | [First transfer](paralympics-2022-canada-norway/RESULTS.md): 142 provisional candidates versus 128 published shots; 100 readable counter updates |
| Korea–China 2022 Paralympics, full match | Official numbered-shot pages, no video timestamps | Not computable | Unknown | [Frozen first transfer](paralympics-2022-korea-china/RESULTS.md): 103 provisional candidates versus 96 published shots; 81 readable counter updates and nine colour conflicts |
| Wetzikon 2025 | Reserved | Not run | Unknown | Preserve for later independent check |

The two hash-selected second windows jointly show 13/13 agreement with the
unchanged saved 2024 timelines, without an unmatched prediction inside either
window. Their plans selected intervals by source hash before source review;
reference and sheet hashes were frozen before predictions were opened. This
supports development of the 2024 split-screen adapter but does not override
the lower first-transfer scores above. Both windows are only five minutes,
their source-only references are same-agent and sampled at one second, and the
full timelines have explicit gaps outside these windows. The engineering
acceptance target remains **not achieved**.

The same left-view departure configuration emitted zero events from the right panel
on the exploratory interval. This is a diagnostic of unsupported camera semantics,
not an estimate of right-panel recall. Panels, travel direction, rink location and
active end cannot be assumed from the old fixed rectangle. A longer video may
switch which view supplies the departure observation.

The same-production Canada–China 2024 transfer is documented in
`canada-china-2024/RESULTS.md`. Its first score is below target despite the
Italy-fitted corridor. The missed stone first appears beyond the y=60 gate; four
accepted false events include changeover/player movement. The source is now
development data, and any post-score improvement on it needs another untouched
recording for a generalization check.

The follow-up Canada–Estonia transfer froze the two-line and motion-confirmation
rule before source inspection. Its first score of 13/0/4 shows the rule does not
transfer high recall even within the 2024 camera family. Three real stones were
withheld by its fixed image-speed cutoff; another was first visible beyond both
gate lines. The untouched score and post-score audit are preserved in
`canada-estonia-2024/RESULTS.md`. Multi-line pooling and a development-fitted
speed cutoff are therefore insufficient for the required high-F1 detector.
An experimental line-independent motion-span candidate layer, run only after
the Estonia first score, recovers all coarse windows on the three exposed 2024
intervals. Its unchanged corridor still admits 7, 7 and 5 unmatched candidates
on China, Italy and Estonia. It addresses the fixed-line recall failure, but
its false events require a stronger stone-versus-player and camera/end-phase
confirmation signal before promotion or another untouched transfer check.
The subsequent motion-context confirmation was fitted on China, Italy and
Estonia, then frozen before a Canada–USA source-only reference. Its first
Canada–USA score was 19/1/1 (precision and recall 0.95). The sole extra and
miss are the same yellow delivery falling 0.552 s before a coarse reference
boundary. A one-second post-score sensitivity check matches 20/20, but the
zero-tolerance first score remains the transfer result. See the
[illustrated result](canada-usa-2024/RESULTS.html) or the
[technical record](canada-usa-2024/RESULTS.md). This partial, same-production check cannot
establish full-recording or cross-layout reliability.

The Canada–Italy first pass is preserved under `canada-italy/`: the selection,
source-only sheets and `blind-reference.json` precede `frozen-probe/` and
`frozen-score.json`. Source review after scoring confirmed two genuine red/yellow
deliveries moving in **positive y** at about 1691 and 1796 seconds; the frozen
negative-y-only detector missed both. Its extra yellow event around 1853 seconds
falls during end changeover, with the receiving view empty. The previously
developed brightness screen accepted this extra event, showing that appearance
alone does not reject every moving player or equipment object.

An exploratory two-direction pass on this now-exposed development recording
finds all 17 labelled windows, but adds three extras (precision 0.85, recall 1.00,
F1 0.919). These are **not** held-out improvements. One extra is the original
changeover event. Source frames around 1843 and 2416 seconds show player/equipment
movement in the positive-y view rather than a new delivered stone. Pooling both
motion directions therefore does not solve high precision. A camera/end-phase
model must decide which direction and view are valid, and should corroborate a
passage with an actual stone and ensuing motion.

A declared center-ice corridor, x=160±60 pixels in the normalized left panel,
withholds those three extras and retains all 17 coarse Italy labels. Its 17/0/0
score is **retrospective development fitting**, not a validation result: the
geometry was chosen after seeing the Italy misses and extras. All withheld
candidates remain in `canada-italy/corridor-screen.json`, with a separate score
in `corridor-score.json`. The next different-production recording was selected
in `paralympics-2022-canada-china/SELECTION.md` before any inference. Its first
score must use this frozen corridor unchanged, even if the layout makes it fail.

That first camera-family check did fail. The 2022 broadcast changes among
close-ups, overheads and full-frame side views rather than keeping the 2024
left/right split. The frozen detector emitted zero events across 20 source-only
delivery windows. The bidirectional variant emitted two events: one unmatched
and one coincident with a yellow delivery but classified red. The unchanged
corridor withheld the unmatched event and retained the wrong-colour one. Its
event-only F1 is 0.095, while **colour-aware F1 is 0.000**. The 2024 corridor
score therefore cannot be generalized to this broadcast. `paralympics-2022-canada-china/`
preserves selection, source-only reference, all predictions and first scores.

The later Beijing-specific visual fallback brings the Canada–China count to
19/1/1 (precision and recall 0.95) against its **original** coarse blind
reference. The remaining mismatch is P10: source review subsequently placed
its release outside the original blind window. That post-score correction is
preserved separately and cannot be used as independent validation. On the
untouched Sweden–Switzerland match, the frozen first pass scored 17/0/2 against
19 blind windows. Both misses were real observed motion: one graphic gap wider
than the allowed 35 seconds, and one throw near the right interval boundary
whose graphic changed only afterward. The revised visual corroboration recovers
both on that **same exposed recording**, giving 19/0/0 interval agreement as a
development fit. Its stricter point-time agreement is 17/2/2. The revision also
preserves Canada–China's 19/1/1 interval score.

Before running the revised candidate on Slovakia–USA, its code hashes and
interval were frozen in `paralympics-2022-slovakia-usa/SELECTION.md` and its
source-only sheets were inspected. Those stills were insufficient for a
defensible exhaustive event/colour reference; `REFERENCE_STATUS.md` records
the decision before inference. The 16 emitted events and unresolved graphic
transitions are a coverage probe, **not an F1 score**. All these samples are
partial match intervals from one production family; none meets the stated
full-recording, cross-family acceptance gate.

That coverage probe exposed a transient two-row count rise at 2444 s that the
state machine had treated as an end reset after only one sample. The revised
reader requires a second rise observation within 15 s. On all three recordings,
the event lists remain identical; the Slovakia–USA unresolved
transitions fall from three to one. The exact revised reader hash and outputs
are preserved as `development-v8-reset-confirmed.json` in each recording folder;
Canada–China and Sweden–Switzerland have corresponding interval scores. This
fix improves state integrity, not measured event F1.

`prototype/scripts/build_event_review_windows.py` now turns an event artifact
into per-event clips using the full evidence bracket, 20 seconds of earlier
context and 45 seconds of later context, clipped to the declared source
interval. It preserves overlapping windows and marks physical start/end as
unknown. Generated `development-v8-review-windows.json` files contain 20, 19
and 16 windows for Canada–China, Sweden–Switzerland and Slovakia–USA. These are
usable analysis/review units, **not validated physical throw segments**; their
quality inherits any event misses or false positives.

The earlier counter-only stage used a red/yellow *remaining-stones* graphic that stays
on screen through many camera cuts. A Beijing-2022-specific reader now extracts
the two counts and emits a colour-labelled event when one stable count drops.
It records the bracket from the last old count to the first new count, rejects
unreadable graphics, and does not invent timestamps for multi-throw gaps. A
one-second point score on the original blind reference is 11/7/9 (F1 0.579).
Matching the declared evidence brackets, each limited to 35 seconds, gives
17/1/3 (F1 0.895). These are different timing claims, so both scores remain.

Source review after scoring found that the original P10 window began after the
visible red release at about 2152 seconds. `postscore-reference.json` changes
only that window and explicitly marks itself non-independent. Against it, the
interval score is 18/0/2 (precision 1.00, recall 0.90, F1 0.947). The two
remaining misses are the **last deliveries of their ends**: the graphic changes
to a compact layout and keeps its final icon during stone travel, so a count
decrement is never observed. Source frames show both delivered stones. A visual
stone-motion fallback was then added as described above. Camera/layout
recognition, full-match testing and independent labels remain necessary. This
adapter still provides neither release timing, trajectories nor settled boards.

## First appearance-screened candidate pipeline

The frozen detector was not changed. A separate appearance screen samples recorded
source frames within ±0.30 s of each gate crossing and measures cap-region
brightness. The threshold was chosen after inspecting the two player-head tracks
and the 16 original development tracks, so this is an **in-sample correction**.
It retains every raw event and adds a status; no event disappears from evidence.

| Development recording | Raw candidates | Stone-appearance candidates | Withheld with reason |
| --- | ---: | ---: | ---: |
| Canada–Korea | 16 | 16 | 0 |
| Canada–Slovakia | 15 | 13 | 2 (`T01`, `T14`, both reviewed player-head tracks) |
| Canada–Italy | 16 | 16 | 0 (including its changeover false event) |

The corresponding review-interval builder emits 16 and 13 provisional intervals.
The two withheld candidates remain in its output. It leaves the interval before
the first accepted passage unassigned and never asserts a physical throw ending.
This is progress on the two known false events, **not a measured high F1**. A dark
real stone may be withheld; lighting and camera changes remain untested.

Artifacts: `canada-korea-screen.json`, `canada-slovakia-screen.json`, and the
matching `*-segments.json` files. Each preserves input and code hashes.

```sh
feasibility/scripts/python.sh prototype/scripts/screen_passages.py \
  --video validation/exploratory-transfer/canada-slovakia.mp4 \
  --events validation/exploratory-transfer/run-01/results.json \
  --output /tmp/new-screen.json
feasibility/scripts/python.sh prototype/scripts/build_screened_segments.py \
  --events validation/exploratory-transfer/run-01/results.json \
  --screen /tmp/new-screen.json --output /tmp/new-segments.json
```

## Engineering acceptance target (not achieved)

The proposed target is precision **at least 0.95** and recall **at least 0.95**
on each of at least three complete recordings from distinct camera/layout families,
with an aggregate F1 at least 0.95. Record raw counts and confidence intervals;
small end-level samples can hide substantial uncertainty. Evaluate all throws,
camera switches, view changes, occlusions, collisions and quiet periods. No tuning
on the final evaluation recordings. Invalid/undecodable source intervals are
reported as coverage failures rather than quietly omitted. Deterministic output
also needs pinned media/config/model hashes and repeatable discrete decisions.

This is a target for discussion, not a claim that 0.95 is sufficient for coaching
or simulation. Board completeness and physical stone-position error need separate
acceptance gates. If a source family misses the target, report it directly.

## Labelling without burdening the user

- Use existing publisher annotations for stone detection and tracking components.
  [CurlObserver](https://github.com/CurlObserver/dataset) provides those, but its
  labels do not certify throw-event intervals over whole matches.
- For end-to-end event F1, create exhaustive interval references for additional
  recordings without asking the user. References prepared blind to predictions
  by an agent are useful development measurements, but carry same-team bias.
  Preserve source, protocol and label hashes before running inference.
- An independent human or licensed third-party event dataset is ultimately needed
  to make an independent claim. The user does not need to do that work. Until then,
  use the explicit reference-method field and report limitations.

## Next detector design

1. Discover camera layout, active sheet and direction from evidence, keeping an
   explicit unknown state when ambiguous. Run more than one candidate view.
2. Replace the tiny frozen colour/neutral-band proposal rule with a stone detector
   measured on the publisher's match-separated data; distinguish players/equipment.
3. Associate stone tracks through time and require a supported departure passage.
   Record first observed time, gate crossing, confirmation time and observation gap.
4. Corroborate with receiving-view arrival when possible. Preserve unmatched or
   occluded passages as candidates, with reason codes; do not invent trajectory.
5. Segment by the next supported throw for review while leaving physical throw end
   unknown until motion/board stability is supported.
6. Freeze each candidate version, run full recordings including negative intervals,
   and report per-source precision/recall/F1 and failure categories.

After this gate, build evidence-backed before/after board observations with
unknowns and persistent identities, then an explicit adapter to an established
curling game-state/simulator format. A 3D simulation will be a **model prediction**
conditioned on observed state and ice parameters; hidden portions of a throw are
not recovered from video alone. Any coaching agent should cite the observed
frames, inferred quantities, uncertainty and simulated alternatives separately.

## Reproduce the existing development score

```sh
feasibility/scripts/python.sh scripts/score_throw_events.py \
  --reference validation/throw-event-benchmark/canada-korea-reference.json \
  --predictions validation/throw-event-benchmark/canada-korea-predictions.json \
  --output /tmp/canada-korea-score.json
```

The reference and prediction copies retain the source's original archived data.
`canada-korea-score.json` records the exact input and scorer hashes.
