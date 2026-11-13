# Layout preflight and adapter dispatch — 7 October 2026

The pairwise camera-motion cue now uses the same source-hashed layout
preflight. Its [routing and cross-resolution audit](CAMERA-MOTION-ROUTING.md)
covers 2022 single-view and 2024 split-view source frames at both 1080p and
360p; it remains development motion evidence rather than an event decision.

`prototype/scripts/run_throw_pipeline.py` samples source frames, records
five-minute layout chunks, and runs an existing adapter only when every chunk
agrees. It recognizes the development 2024 split-screen production via a pale
left overhead view and blue right scoreboard area, or the Beijing 2022
production via its readable remaining-stone counter. Mixed or insufficient
evidence yields `layout: unknown` and no confirmed events. It does not infer
camera geometry for other broadcasts.

For a processed split-screen recording, add `--audit-source-activity` (and
`--allow-partial` when the full source has unknown layout chunks) to write
`source-activity-audit.json` and `source-activity-coverage.json` beside the
timeline. The audit samples both panels every five seconds and subtracts long
static-left/active-right spans from the *left-trigger-supported* time. The
runner checks source, interval and code hashes on resume. It accepts 16:9
source sizes by normalizing frames to the audit's 640×360 panel geometry.
Existing event candidates remain unchanged; the sidecar reports detector-blind
coverage and does not identify throws. This option uses a development threshold
chosen after the Latvia and Italy failures, so its absence is not proof of
continuous detection coverage and its presence is not a recall estimate.
Add `--probe-blind-right` with that option to preserve two further sidecars:
`right-motion-in-blind.json` contains all 1 Hz coloured-motion tracks in the
flagged intervals, and `right-entry-review-in-blind.json` contains the
fixed-rule early-line review tier. Both files are source/code-hash checked on
resume. They surface possible throws in a dead left view but do not add
accepted events, prove stone identity or count deliveries. The runner also
writes `right-entry-camera-fusion.json` and `candidate-review-union.json`:
the latter orders every raw split-view left proposal and any Beijing adapter
observations with unlinked right-entry reviews, while keeping
context-confirmed and withheld left candidates distinct. A
time/colour link enriches a left candidate; it does not create another throw.
Each split-view left candidate carries the observed interval from first
tracked appearance to confirmation; each right-only entry carries its short
tracked prefix interval. These bound motion evidence for review, not physical
release and settle times or a complete throw trajectory. The union pins the
raw per-run artifacts used to recover those intervals.
For older split-view runs that have saved `raw.json` and `events.json` but no
`triage.json`, the union reconstructs the same lossless dispositions from
those two artifacts and records both hashes plus the triage-code hash. It
rejects a source, interval or accepted-event disagreement.
With `--observe-blind-right-boards`, the runner additionally writes
`right-only-partial-caps.json`: 15/20/25-second source-image samples after
each right-only entry. It evaluates the entry's measured crossing bracket as
well as its interpolated timestamp, abstaining when the visible cap set or
scene status changes within that timing uncertainty. These are camera-local
colour blobs, not complete post-throw boards or verified settled stones. A
`candidate-state-handoff.json` then attaches those partial observations to
the ordered candidate ledger, leaving physical event, identity, metric board,
settle time and simulation fields explicitly unknown.
With `--compare-blind-right-boards`, the runner also writes
`right-board-sequence.json`. It compares only adjacent right-only samples,
checks painted-house alignment in the source frames, and abstains across
unusable cap sets or intervening candidates. Its output is a conditional
image-cap change ledger, not a physical stone-transition sequence. The
[Latvia current replay](full-2024-coverage/LATVIA-RIGHT-ONLY-PARTIAL-CAPS.md)
has three usable adjacent pairs and four abstentions; Italy has no right-only
pairs to compare.
With `--observe-left-candidate-boards`, it also samples the receiving
right-view 15/20/25 seconds after **every** split-view left proposal, including
withheld proposals. The scan checks both ends of each observed-motion time
bracket and abstains if another candidate or route boundary intrudes on the
tail. `candidate-state-handoff-v2.json` joins those observations to the
existing right-only rows. It remains a partial image ledger: neither a
verified throw nor a settled physical board is inferred.
With `--compare-all-candidate-boards`, the runner then writes
`candidate-image-board-sequence.json` for **every adjacent candidate pair**.
It compares partial caps only where both samples are usable, their camera
origin and route agree, the first sample precedes the next candidate, and
the painted house aligns at the sampled instants. Every other pair records
an explicit abstention. This is an image change ledger, not physical stone
tracking or game-state reconstruction.
With `--fit-candidate-house-ellipse`, the runner additionally fits the blue
receiving-house paint in all three frames of each usable cap observation.
Only a geometrically stable three-frame fit yields cap coordinates divided
by the image ellipse axes. These are **cap image coordinates**, not rink
metres or stone ground-contact positions; the fit abstains when paint is
occluded or the apparent ellipse changes.
The [held-out line check](full-2024-coverage/HOUSE-CALIBRATION-TRANSFER.md)
rejects transferring the tuned Korea homography to Latvia or Italy by a
simple ring-center/scale adjustment: the independent image line misses by
about ten pixels at 360p in both sources. Metric game-state coordinates
therefore remain unavailable from this transfer.
The [source-specific pilot](full-2024-coverage/SOURCE-SPECIFIC-HOUSE-CALIBRATION.md)
fits a fresh projective transform from ring paint and the hog line. Only 5
of 20 Latvia and 11 of 48 Italy stable-ellipse samples survive withheld-ring
and adjacent-frame checks. Those conditional transforms project cap centers
as if they were on the ice; they are not validated stone positions or a
complete game state.

Preflight-only runs over the fixed 1650–2760 s interval classified all six
on-disk recordings as expected: Canada–USA, Canada–China and Canada–Italy
2024 as `split_2024`; Canada–China, Sweden–Switzerland and Slovakia–USA 2022
as `beijing_2022`. **These are the same recordings used to choose the routing
features and thresholds**, so this is an integration/coverage check rather
than layout-generalization validation. Each `*/preflight.json` preserves
sample times, feature measurements, per-chunk counts and source/code hashes.

Full-video preflight on Canada–USA (0–8633 s) returns **unknown**, preserving
three coverage gaps: 0–300 s, 7500–7800 s and 8400–8633 s. The supported
split-screen runs are 300–7500 s and 7800–8400 s. These are conservative
five-minute blocks, not exact camera transition times. The full recording
therefore has **not** been segmented end to end; `full-usa24-runs/preflight.json`
records the evidence. The runner does not present partial observations as a
whole-video exhaustive event list.

`--allow-partial` now runs each supported span separately and writes
`timeline.json` with `observed_events`, source/run IDs, boundary-review flags,
and explicit `coverage_gaps_s`. It deliberately has no top-level `events`
field that the exhaustive benchmark scorer would accept. `--resume` validates
the saved preflight and completed adapter stages before continuing an
interrupted run; it was used after a long decode was interrupted with only
`preflight.json` present.

On Canada–USA, the five-minute-window partial pass observed 124 events in two
supported runs. A predeclared 90-second-window pass narrowed the conservative
unknown spans to 0–90 s, 7650–7740 s and 8460–8633 s (353 s total) and
observed 130 events. Only two events fall within the 40-second run-boundary
review band. The 20 timestamps and colours inside the original 1650–2760 s
blind-reference interval are identical to the frozen first transfer result.
Across the overlapping long runs, one red passage moved from 7800.976 s to
7798.495 s when its run began earlier; source frames show the same visible
stone movement around 7798–7802 s. This is a timestamp/boundary difference,
not a newly measured true or false event. The 130-event full-video count has
**no exhaustive reference** and therefore no precision, recall or F1 claim.
The 90-second routing choice was made after viewing this recording's
five-minute coverage gaps, so its wider coverage is development fitting.

Source-only 5-second contact sheets of the three remaining gaps are under
`unknown-gap-audit/`. The opening 0–90 s is a title/countdown until the live
split view appears at about 85 s. Much of 8460–8633 s is an empty sheet,
credits or black frames. The 7650–7740 s gap retains live ice and player
movement, so it cannot be certified as no-play from sparse stills. A separate
diagnostic run of the frozen span/context detector over that middle gap found
two red motion candidates at 7704.193 and 7708.070 s, both withheld for
large surrounding motion (2796 and 1891 changed pixels in the 80×80 patch).
Those rejected candidates are **not evidence that no throw occurred**; the
middle gap remains an explicit coverage failure until continuous review or an
independent signal resolves it. The diagnostic outputs are
`unknown-gap-audit/middle-raw.json`, `middle-motion.json` and
`middle-confirmed.json`.
Denser one-second source sheets over 7696–7715 and 7718–7741 s show players
moving around stones already in the house; no new delivered stone is evident
in those sampled frames. That is a retrospective visual observation, not an
exhaustive motion review or independent reference.

`prototype/scripts/build_timeline_review_windows.py` now turns a partial
timeline into per-event review contexts clipped to each supported run. The
Canada–USA 90-second pass produced 130 windows in
`full-usa24-90s-partial/review-windows.json`; two carry boundary-review flags,
and the first window is clipped at the 90 s run start. These windows are
practical inputs for visual or trajectory analysis, not physical throw
segments or settled-board states.

The same runner was exercised over the complete Canada–China Beijing 2022
source (0–8356 s) with five-minute layout windows. It observed 119 events in
counter-supported runs 300–3600 s and 3900–8100 s, preserving gaps at
0–300 s, 3600–3900 s and 8100–8356 s. The 20 events in the previously
measured 1650–2760 s interval match the preserved Beijing adapter output
exactly. The two supported runs also retain 14 unresolved counter transitions.
This is a full-source **coverage and consistency check**, not a new F1 score.
Its 119 gap-clipped review windows are in
`full-china22-partial/review-windows.json`.

The Beijing middle gap is active play. Source frames around 3663–3674 s show
a yellow delivery and the stone moving into the house while the usual
remaining-stone graphic is absent. This is a concrete missed throw in the
current routed timeline. `prototype/scripts/scan_beijing_layout_gaps.py`
probes only unknown spans bracketed by Beijing-supported runs and stores
visual tracks as **unconfirmed gap candidates**, separate from
`observed_events`. Its run over 3600–3900 s found one yellow track at
3668–3671 s, recorded in
`full-china22-partial/gap-motion-candidates.json`. The candidate begins after
the visible delivery and has no validated release timestamp. The gap remains
unknown because this visual fallback has not been independently tested for
precision or recall across camera cuts.

A new whole-source **counter visibility audit** scans that China recording at
one-second intervals without layout-block routing or visual fallback. It read
the Beijing counter in 5,574 of 8,356 sampled seconds (66.7%) and recorded
119 stable decrements plus 16 unresolved counter changes. The five-minute
preflight had marked 7,500 s as supported, yet the counter was unreadable in
1,952 of those seconds. Repeating only the layout preflight with 90-second
blocks marked 1,696 s unknown rather than 856 s; five existing timeline
events fall inside those newly unknown blocks. This shows that a supported
layout block is not continuous event coverage.

The [reconciliation artifact](full-china22-coverage-reconciliation.json)
compares the counter audit with the 119-event partial timeline: 114 events
match exactly in colour and counter-update time; five are audit-only and five
timeline-only. The audit includes a yellow decrement at 3662 s inside the
former 3600–3900 s routing gap, consistent with the independently visible
yellow delivery there. It also records a red decrement at 3629 s with a
3596–3629 s evidence interval spanning the route boundary; that timestamp
cannot establish a new throw after 3600 s. Around 333–350 s the counter
alternates between two yellow counts before stabilizing, so a 350 s update
must not be treated as a precise release time. The audit retains all 8,356
counter samples and readable/unreadable runs in
`full-china22-counter-audit.json`. Neither equal total count nor exact
timestamp overlap establishes whole-recording recall or F1.

The counter audit also exposed a state-machine duplicate at new-end slot
flashes: red 2811/2825 s and yellow 4041/4055 s and 7315/7327 s were each
two updates for one blinking count transition. The revised model ends its
reset grace after the first confirmed decrement. Replaying the **same saved
8,356 observations** removes the three later duplicates, leaving 116 counter
events; the original 119-event audit remains untouched. This is a postscore
fix, not a newly validated whole-match score. Re-running the measured
1650–2760 s intervals on both Canada–China and Sweden–Switzerland produced
exactly the prior 20 and 19 event colour/time/kind lists, respectively.
`full-china22-counter-postscore-replay.json` records the changed event keys.

A frozen third-source gap transfer on the full Slovakia–USA Beijing recording
is preserved under `slovakia-usa22-gap-transfer/`. Three interior 300-second
gaps had seven coarse source-only delivery windows after excluding two
boundary-uncertain portions. The unchanged raw visual scanner scored
5 TP / 15 FP / 2 FN (candidate F1 0.370); the previously development-fitted
ice-scene/episode screen scored 4 / 3 / 3 (candidate F1 0.571). It missed a
visible yellow delivery in one gap and retained a displaced-stone episode as
another delivery. This rejects that screen as a general high-F1 recovery
path. The source-only reference and first outputs remain intact; these are
candidate scores on selected gaps, not full-recording confirmed-event scores.

Two full dispatch checks compared event dictionaries with earlier outputs:

| Routed source | Existing adapter result | Routed result | Equality |
| --- | --- | --- | --- |
| Canada–USA 2024 | frozen first span-context transfer, 20 events, 19/1/1 against its original coarse reference | 20 events, 19/1/1 | Exact event-list match |
| Sweden–Switzerland 2022 | post-score development v8, 19 events, 19/0/0 with a 35 s evidence-interval cap | 19 events, 19/0/0 | Exact event-list match |

The second score is **not a new unseen result**; its event model was revised
after this recording's first score. The router has not been validated on
an untouched layout or exhaustively labelled complete recording. It does not detect all camera
switches between sparse samples, and an accepted layout does not certify
throw recall, exact release time or physical segment boundaries.

The [later whole-recording 2024 coverage audit](full-2024-coverage/RESULTS.md)
found live split-screen play inside the old Italy unknown spans. A
postscore router revision tolerates one false Beijing digit read on an
otherwise stable split chunk and recognizes a darker blue scoreboard
when the pale left ice panel is especially clear. Replaying saved frame
measurements reduces unknown time from 2,040 to 240 seconds on Italy,
873 to 243 on Estonia and 527 to 347 on China; USA stays at 353 seconds.
Three 2022 full-match replays retain their prior unknown spans with no
new 2024 split chunks. Fresh decoding on all three affected 2024 videos
exactly reproduces the replayed chunk layouts. The unchanged Italy
adapter yields 109 provisional events over the newly supported runs;
the same adapter yields 128 on Estonia and 131 on China. Their old
measured 17-, 17- and 18-event intervals remain unchanged. This is improved
layout coverage, not independent event precision or recall.

The [Beijing counter monotonicity audit](MONOTONE-COUNTER-RESULTS.md) found
a stable one-row count rise that the previous state machine promoted and
then misread on its return as another throw. The revised state machine
preserves the last monotone count, records the rise as unresolved, and
produces a new full Canada–China 2022 partial timeline with the same coverage
gaps. Its prior measured intervals retain identical event lists. This is a
development precision correction, not a full-match F1 result.
The [frozen transfer replay](MONOTONE-TRANSFER-RESULTS.md) over two other
full Beijing counter streams finds additional changed event keys; it retains
their source limitations and no full-match F1 claim.
The [counter-in-gap inventory](COUNTER-GAP-RESULTS.md) finds five counter
updates wholly inside unknown route intervals across the three full 2022
recordings. They remain candidates, with three route-boundary transitions
flagged separately; no coverage gap is silently closed.

Example, using an unused output directory:

```sh
feasibility/scripts/python.sh prototype/scripts/run_throw_pipeline.py \
  --video validation/throw-event-benchmark/canada-usa-2024/source.mp4 \
  --source-id Z1yEOv__bDc --start 1650 --end 2760 \
  --output-dir /tmp/curling-throw-run
```

The resulting `preflight.json` records the route. `events.json` and, for the
2024 route, `raw.json` and `motion.json` retain detector evidence. The runner
refuses to overwrite an existing directory and protects the reserved
independent-evaluation recording.

For a complete recording with explicit gaps, add `--allow-partial` and choose
the preflight window with `--layout-chunk-s 90`; the output is `timeline.json`.
If processing is interrupted, repeat the same command with `--resume`. Resume
rejects a changed source, interval, preflight rule or adapter code hash, and
reuses only matching completed stages.
