# Historical repository overview — superseded

This is a historical snapshot, not current instructions. Old transfer/completion wording must be interpreted with the later corrections. See [current pipeline](../CURRENT_PIPELINE.md).

# Curling video research prototype

## Current project scope

Supervisor-approved focus (22 October 2026): **one reliable end-to-end pipeline
for left/right split-screen curling videos**, producing accurate stone
trajectories without manual recalibration or per-video rule tuning. Necessary
camera alignment must be automatic within the same pipeline. Broad transfer
learning and other broadcast formats are deferred; the remaining project
objectives are retained, with trajectory reliability the main priority.

Success requires checking detection, observable-track continuity, cross-camera
identity, geometric accuracy, coverage and the synchronized video/trajectory
viewer together. The historical results below do not establish that success.

**Completed meeting evidence audit (22 October 2026, 09:30):** Open the
[French report](../../validation/meeting-2026-10-22/summary.html),
[printable PDF](../../supervisor-progress-2026-10-22.pdf), or
[detailed measured profile](../../validation/meeting-2026-10-22/index.html).
Current full public runs: Sweden 2024 event-context precision/recall **95.2%/97.9%**,
120.4 minutes processing; Beijing **88.9%/89.6%**, 132.2 minutes processing.
Current partial projected segments: 121/147 and 27/126 candidates respectively.
The archived control reproduced exactly, but faithful Sweden transfer produced
zero cross-view links because receiving calibration failed. Reliable complete
trajectory generalization is **not established**. The
[current viewer](../../validation/meeting-2026-10-22/runtime/index.html) contains all 273
current candidates; every selection was browser-tested. The detailed brief
separates current endpoint measurements, earlier development outputs and
retrospective label corrections.

The [development viewer](../../validation/integrated-pipeline-final/index.html)
contains all 287 candidates from two recordings, including missing tracks.
Source-point checks establish whether projected observations land on visible
stones; they do not establish correct physical trajectories or metre accuracy.

Existing frozen event results can be completed without changing detections:

```bash
feasibility/scripts/python.sh prototype/scripts/complete_throw_trajectories.py \
  --video path/to/source.mp4 --events path/to/timeline.json \
  --output path/to/new-run/aggregate.json
```

For a 2022 candidate ledger, also pass `--motion-review path/to/shot-review/manifest.json`
to recover within-camera motion coordinates. Failed or ambiguous association
and unavailable calibration remain in the final output. Per-event caches are
fingerprinted and resumable; changed inputs or code require a new output directory.

**Evidence correction (15 October 2026):** The former capstone final report's
all-steps-complete status, centimetre accuracy table, synthetic commentary
factuality claim, and purported coach ratings were withdrawn. See the
[evidence and open-gates summary](../../docs/CAPSTONE_FINAL_REPORT.md). The
[interactive rink page](../../prototype/demo/index.html) contains illustrative
hand-authored scenarios, not video-derived replay.

**Latest performance audit (16 October 2026):** The [frozen same-family sweep](../../validation/same-family-sweep-2026-10-15/RESULTS.md)
reruns seven exposed full 2024 recordings and one previously unanalysed
Canada–Norway recording with the unchanged candidate pipeline. It measures
coverage, raw/accepted/review counts, and concrete false-event mechanisms;
none has an independent exhaustive full-video event reference. The Norway
transfer has 102 accepted candidates against a nominal six-end capacity of
96, with excess red labels, so complete-match throw accuracy is not established.

A source-specific experiment for converting curling video into timestamped stone observations, throw passages, partial trajectories and provisional links between two camera views.

**Start here:** [the 9 October supervisor progress report](../../supervisor-progress-2026-10-09.html)
summarizes the current evidence, gaps, demos and next milestones. The older
`supervisor-briefing.html` records the September feasibility briefing;
`prototype/cross-view/index.html` is the two-view demo. Local viewers need
their surrounding data and video files. The generic upload page is an older
image indexer and does not run the advanced pipeline.

The [Canada–China full-match demonstration](../../prototype/full-match-canada-china/index.html)
now presents 125 provisional event windows over the complete 2h19m source
alongside all 125 official post-shot reference boards and 30 linked partial
boards recovered from video. Matching event and official-shot totals are not
evidence of full-match F1; no state is simulation-ready.
The [Canada–Czechia event-to-state viewer](../../prototype/full-match-canada-czech-state/index.html)
now steps through 79 provisional passages with source video, 66 post-event
partial boards and 40 adjacent same-camera comparisons. It marks missing
boards, camera changes and unresolved physical identity explicitly; it is a
video-evidence replay, not a physics simulation.
The separate [development replay](../../prototype/full-match-canada-czech-state-development/index.html)
shows 91 candidates after a wider left-camera search, with 78 partial boards
and 56 adjacent comparisons. Its 12 additional paths are source-visible but
not independently verified deliveries.

**Next milestone:** [throw-event measurement gate](../../validation/throw-event-benchmark/README.md)
sets an explicit precision/recall/F1 target across different recordings. A
separate appearance screen withholds two known player-head candidates and builds
provisional review intervals while preserving all raw evidence. The detector remains
source-specific today. On a new Canada–Italy recording, the unchanged detector
scored 15 true events, 1 extra and 2 misses against a coarse blind agent reference
(F1 0.909); opposite-direction tracking recovered the misses but created more
extras. These development scores do not establish generalization. Game-state,
simulation and coaching layers follow only from supported observations.

On a different 2022 Paralympics broadcast, that fixed left-panel detector found
none of 20 coarse agent-labelled throws. Its camera/layout assumption is a
blocking failure for the cross-recording high-F1 objective; see the benchmark
for the frozen results. A Beijing-specific broadcast counter reader plus visual
stone-motion corroboration now scores 19/1/1 against the original 20-window
blind reference on that development recording. Its frozen first pass on another
match scored 17/0/2 against 19 blind windows; recovering those two misses after
review produced an in-sample 19/0/0 interval score, not independent validation.
An untouched third broadcast has 16 emitted events but no defensible exhaustive
reference yet. Exact release times, full-match cross-camera F1, game-state
reconstruction and simulations remain open work.

A further same-production Canada–China 2024 transfer scored 17/4/1 (F1 0.872)
with the Italy-fitted bidirectional corridor. Moving its y=60 line to y=80
recovered the miss but badly reduced Canada–Italy recall. An experimental
two-line union recovered all coarse labels on both exposed 2024 intervals while
adding five and four false candidates, respectively. The active detector problem
is distinguishing a delivered stone from similarly moving players/equipment and
selecting the correct camera/end phase; see the [preserved transfer results](../../validation/throw-event-benchmark/canada-china-2024/RESULTS.md).
An added confirmation rule reached 1.00 F1 only on those exposed intervals.
Frozen before Canada–Estonia, it scored 13/0/4 (F1 0.867) on a new partial-match
source: three genuine throws fell below its pixel-speed cutoff and one stone
first appeared beyond both virtual lines. The [first transfer audit](../../validation/throw-event-benchmark/canada-estonia-2024/RESULTS.md)
preserves this failure; high-F1 validation remains open.
An experimental line-independent motion-span detector plus local frame-change
confirmation was then frozen before a Canada–USA transfer. Its first score on
20 coarse source-only windows was 19/1/1 (precision 0.95, recall 0.95,
F1 0.95). The sole extra and miss refer to one yellow passage 0.552 s before
the labelled window; a one-second tolerance matches all 20 in a post-score
sensitivity check. [The preserved result](../../validation/throw-event-benchmark/canada-usa-2024/RESULTS.md)
is a partial-match, same-production test, not cross-family or complete-match
validation.
An experimental [layout preflight and adapter runner](../../validation/throw-event-benchmark/layout-router/README.md)
now routes the two known production families, records five-minute layout
evidence, and returns unknown on mixed or unsupported layouts. It reproduced
the existing event lists on one 2024 and one 2022 source. Its routing features
were selected on these recordings, so this is integration progress rather than
new cross-family accuracy evidence.
The runner can also retain a [partial full-recording timeline](../../validation/throw-event-benchmark/layout-router/README.md)
with explicit coverage gaps and resumable adapter stages. On Canada–USA, a
90-second-window development pass observed 130 passages while leaving 353 s
unknown; no full-match precision or recall can be inferred from that count.
A later [whole-recording 2024 routing audit](../../validation/throw-event-benchmark/layout-router/full-2024-coverage/RESULTS.md)
found live play in Italy spans the original colour signature marked
unknown. The revised, replayed router reduces Italy's unknown time from
2,040 to 240 seconds without changing three sampled 2022 routes. The
unchanged adapters now record 109 Italy, 128 Estonia and 131 China
provisional events in supported runs; all three earlier measured
event lists reproduce exactly;
whole-recording event F1 remains unknown.
A complete Beijing 2022 recording produced 119 routed observations with
three coverage gaps. Source review exposed a real yellow throw inside its
middle gap; a new visual scan preserves the motion track as an unconfirmed
candidate, not a confirmed event. This shows that view-gap recall remains a
material blocker even when the known-layout event lists reproduce exactly.
A continuous one-second counter audit found the graphic unreadable for 2,782
seconds, including 1,952 seconds inside blocks the five-minute router called
supported. Its 119 counter decrements overlap only 114 of the 119 routed
events exactly; [the coverage reconciliation](../../validation/throw-event-benchmark/layout-router/README.md)
keeps the mismatches and unreadable spans explicit. Full-recording F1 is
still unmeasured. A preserved postscore replay of those same counter samples
removed three duplicate updates caused by blinking graphic slots; the two
existing measured match intervals retained their original event lists.
A frozen visual-gap transfer on Slovakia–USA 2022 then scored only 4 true,
3 extra and 3 missed coarse throws (candidate F1 0.571) after the
development-fitted ice-scene screen. The [preserved failure](../../validation/throw-event-benchmark/layout-router/slovakia-usa22-gap-transfer/RESULTS.md)
shows that local stone motion plus scene filtering still fragments one throw,
confuses displaced stones and misses camera-cut deliveries.
A [post-score bright-body probe](../../validation/throw-event-benchmark/layout-router/bright-body-probe/README.md)
recovers all seven coarse gap throws as raw candidates on that exposed source,
but adds 25 false candidates and regresses on another exposed Beijing gap.
It remains a diagnostic, not a promoted throw detector.
A [public-label learned stone-box probe](../../validation/curlobserver-learned-probe/README.md)
improved the fixed 25-image component score from 8/102 to 78/102 matched
boxes, but produced 46 raw motion tracks for two coarse throw windows in a
changing-view gap. Its unchanged screen matched only one window with the
correct colour. Stone recognition alone does not resolve delivered-versus-
displaced identity or camera-cut continuity. Follow-up dense-gap development
combined learned boxes with a smooth large-cap motion fallback. It matched
all seven coarse throw windows on an exposed Canada–China 2022 interval and
all six on the next source-only interval without extra temporal candidates.
The latter had two wrong stone colours (colour-aware F1 0.667); both intervals
come from the same match, so this remains a prototype rather than a high-F1
full-video validation. The [preserved results](../../validation/curlobserver-learned-probe/README.md)
document the first scores and colour failure.
An episode-colour rule corrected those two exposed mistakes. On the next
source-only interval spanning an end transition, its frozen first score was
4/0/1; a later two-channel motion agreement rule recovered the miss only
in a postscore analysis. Its frozen transfer added no extras on one other
match gap or an opening negative segment. These remain small development
checks, not full-recording high-F1 evidence.
A fixed later Slovakia–USA span supplied an automated counter-concordance
check: the counter was readable for 293/300 seconds and showed six stable
decrements, while the frozen visual fallback emitted seven candidates. All
six decrements have a temporal candidate, but one candidate has the wrong
colour and one red candidate is unmatched. Source review exposed the core
failure: a displaced red stone near the house can move more than the delivered
yellow stone, misleading the episode-colour rule. This is weak broadcast
concordance, not independent event F1.
A postscore camera-registration probe showed that the extra house-stone track
mostly followed camera motion, while the delivered yellow stone moved relative
to the ice. A moving red shirt also passed that relative-motion check, so
camera compensation is diagnostic evidence rather than a throw decision rule.

The newer [broadcast-shot evidence study](../../validation/curlobserver-learned-probe/shot-origin-study.md)
combines delivery-side view probability, within-shot cap and learned-box motion,
and delayed counter changes without requiring development labels for inference.
Its full Canada–China 2022 scale run covers 630 shots; after a postscore
counter replay it pairs 115/116 stable counter updates to candidates only
under a permissive temporal check. This is a coverage diagnostic, not
independent throw-event F1. An unseen throwing side, counter gaps, exact
release timing and physical stone identity remain unsolved. A separate
travel-view route preserves one counter-backed candidate whose release
view is absent or unusable; the [ordered evidence ledger](../../validation/curlobserver-learned-probe/china-full-transfer/README.md)
keeps these windows and counter-state gaps explicit.
The [frozen second full-match transfer](../../validation/curlobserver-learned-probe/slovakia-full-transfer/RESULTS.md)
applied the same rules to Slovakia–USA 2022 and linked 94 of 98 readable
counter updates to candidate events, leaving four unlinked and 25
visual-only candidates. That is cross-match development evidence, not
independent event precision or recall.
A preselected Slovakia source-only check then found 13/13 coarse
deliveries temporally covered by 14 eligible candidates (development
F1 0.963), with two wrong-colour matches and two unknown colours;
colour-aware F1 is only 0.667 under the same coarse overlap rule.
The [full result](../../validation/curlobserver-learned-probe/slovakia-full-transfer/RESULTS.md)
keeps that small, agent-authored diagnostic separate from the independent
full-recording acceptance gate.
The [2022 counter monotonicity audit](../../validation/throw-event-benchmark/layout-router/MONOTONE-COUNTER-RESULTS.md)
now prevents a stable one-row count rise from becoming a false decrement on
its return. A fresh full Canada–China routed run preserves three explicit
coverage gaps and 117 provisional events; its old measured intervals retain
the same event lists. Full-match precision and recall are still unmeasured.
The [third full-match development transfer](../../validation/curlobserver-learned-probe/swiss-full-transfer/RESULTS.md)
ran on Sweden–Switzerland 2022 with a Swiss-excluding origin model. It
linked 99 of 103 readable counter changes to 121 candidates. Fifteen
hash-selected, agent-reviewed deliveries in three short windows all had
temporal candidate overlap, but one matched colour was unknown and 22
full-match candidates lacked counter links. This still does not meet the
independent complete-recording precision/recall gate.

An [official Beijing 2022 shot-order ledger](../../validation/official-shot-sequence/PWG2022-SHOT-REFERENCE.md)
now supplies independent numbered deliveries for the China, Slovakia and
Switzerland match videos. Their official shot totals are 125, 112 and 112,
versus 133, 119 and 121 full-video development candidates. The official
pages have no video timestamps, so these differences expose unresolved
candidate errors without yet providing event F1.
The [2022 shot-reference audit](../../validation/official-shot-sequence/PWG2022-SHOT-REFERENCE.md)
now anchors 300 of those 349 official shots to unique, colour-consistent
broadcast counter observations. A source-video post-cut colour check resolved
45 of 64 visual-only candidate colours without using the official labels,
including eight corrections from red to yellow. An official-order sequence
audit retains ambiguous and skipped candidates explicitly; it is a diagnostic,
not independent full-video throw-event F1.
A conservative [duplicate-evidence fusion](../../validation/official-shot-sequence/PWG2022-SHOT-REFERENCE.md)
groups two wholly contained Swiss visual candidates into one counter-backed
release episode, preserving all source IDs. Across the three 2022 ledgers this
changes 373 raw candidates to 371 provisional event groups; independent
timing validation is still needed before making it a production suppression.
A visual-only cap-motion stage matches delayed counters for 29/32 shots in
the only two fully counter-anchored 2022 ends; the existing post-cut motion
rule lifts that weak proxy to 30/32 without an extra candidate. The remaining
two misses are camera-change cases, and these counter-proxy scores are not
independent throw-event F1.
An early held-cap release cue recovered both remaining China end-4 misses in
an in-sample proxy check. Its first 74-window 2022 transfer also exposed a
Swiss red-jacket false positive; a postscore ice-context gate removed that
case. The resulting 32/32 complete-end counter-proxy agreement is a
development ceiling, not cross-layout or full-video validation.
An [untouched Canada–Norway 2022 full-match transfer](../../validation/throw-event-benchmark/paralympics-2022-canada-norway/RESULTS.md)
then found 142 provisional candidates against 128 official shots. The frozen
held-cap rescue added none in 32 eligible windows. On the sole fully
counter-anchored end, 15 of 16 cap candidates matched delayed counter times,
but four matches had conflicting colours and two had unknown colour. This
transfer exposes both excess candidates and identity errors; it is not
independent throw-event F1.
The [official post-shot diagram reference](../../validation/official-shot-sequence/PWG2022-BOARD-STATE.md)
now provides 349 source-linked 2D board snapshots and delivery-to-state
transitions for those same matches. It is a benchmark for future video game
state reconstruction, not a claim that the video pipeline has recovered the
boards or physical trajectories.
The first video-board check matched all ten stones in one clear Canada–China
overhead frame, but the fixed three-game transfer audit found a complete board
match for only one of 15 sampled shots (seven passed the overhead-view filter).
This exposes a camera-view and occlusion gate that must be solved before video
observations can reliably populate game states.
A conservative connected-ring gate now completely matches three of five
accepted frames in the same 15-shot audit. A field-of-view check finds that
six of 24 official stone symbols in those accepted diagrams project off-frame
or near the edge, so a close-up can only supply a partial board state.
Temporal consensus over nearby overhead frames emits seven partial boards
on the same 15-shot development sample. All 22 emitted stone positions match
the official diagrams; five boards are complete. Eight shots still yield no
stable board, and this selected sample cannot establish board recall or
throw-event F1.
A [video-derived partial-board handoff](../../validation/official-shot-sequence/pwg2022-video-partial-board-observations.json)
now exports those seven snapshots and 22 stones with source hashes, local
coordinates and temporal support. It explicitly marks completeness and
simulation readiness unresolved; official diagram positions are excluded
from runtime state.

**Current work (7 October):** [automated exploratory transfer](../../validation/exploratory-transfer/README.md)
ran the frozen detector on Canada–Slovakia and exposed two player-head false events
among 15 provisional passages. A [published-label component probe](../../validation/curlobserver-probe/README.md)
matched 8/102 stone boxes on 25 fixed images; this tested the old proposal stage,
not the calibrated body detector. No user labelling is needed for this development
route. The [independent review packet](../../validation/unseen-end/README.md) remains an
optional future check; reserved Wetzikon footage is still excluded. See also the
[earlier-gate study](../../prototype/gate-study/README.md).

An [official 2024 game-results audit](../../validation/official-shot-sequence/README.md)
now compares three provisional whole-match event totals with the published
Canada–China, Canada–Estonia and Canada–Italy end scores. The book has no
shot-by-shot pages for these games, so its nominal per-end counts are a
sequence consistency check, not an event reference or F1 score.
The [China end-by-end source review](../../validation/official-shot-sequence/china-end-count-audit.json)
finds 127 candidates after four likely non-stone tracks are excluded: seven
ends with 16 candidates and a final end with 15 before the broadcast closes.
An [automatic 2024 scoreboard-marker probe](../../validation/official-shot-sequence/END-MARKER-TRANSFER.md)
reads end order across all three recordings after calibrating the graphic's
position and column width. Its update can lag play, so it supplies context
without defining physical throw or end boundaries.
The [source-linked display ledgers](../../validation/official-shot-sequence/END-MARKER-TRANSFER.md)
attach locally bracketed broadcast end states to provisional events while
leaving physical end assignment unknown; one China event visibly demonstrates
the graphic lag.

The [2024 tracked-object identity probe](../../validation/official-shot-sequence/IDENTITY-PATCH-TRANSFER.md)
retained only 2 of 17 source-window-matched Italy stones with a frozen
China-trained appearance model, so no hard appearance veto was added.

The [candidate-object catalog](../../validation/official-shot-sequence/CHINA-CATALOG-REVIEW.md)
shows one China track merging a person into a moving red stone. A
[motion-episode audit](../../validation/official-shot-sequence/MOTION-EPISODE-RESULTS.md)
isolates its observed moving segment near 6876.1 s without claiming an exact
release time or validated throw score.

## Set up

Recorded environment: Linux, Python 3.13. Native video preparation also uses `ffmpeg` on PATH.

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m playwright install chromium
```

On Windows, use `.venv\Scripts\python.exe`. On ordinary Linux/macOS, `.venv/bin/python` works directly. The `feasibility/scripts/python.sh` wrapper supplies library paths required by this project's Nix host. `CURLING_PYTHON` can select another Python executable. A fresh Linux/Python 3.13 installation succeeded without system site packages. `requirements-lock.txt` records its direct and transitive package versions; use it instead of `requirements-dev.txt` to recreate that complete package set. Other operating systems have not been tested.

## Validate

```sh
feasibility/scripts/python.sh scripts/validate.py
# With the recorded experiment data present:
feasibility/scripts/python.sh scripts/validate.py --artifacts
# With source videos and Playwright also present:
feasibility/scripts/python.sh scripts/validate.py --artifacts --browser
```

The runner checks syntax, unit/integration tests, dependency consistency, lint and formatting. Optional checks recompute stored metrics and launch a temporary loopback server for browser tests. It writes `validation/report.json` and individual logs. `CHROMIUM_EXECUTABLE` overrides browser discovery; `CURLING_BROWSER_PYTHON` selects a separate Playwright environment if needed.

See [the audit](../../validation/AUDIT.md) for what was checked and remaining limitations. Software tests do not establish real-world vision accuracy.

## Implementation map

| Component | Code | Responsibility |
|---|---|---|
| Calibration and registration | `prototype/vision_core.py`, `prototype/rectification_core.py` | Pixel-to-ice homographies, ring refinement, SIFT/LK registration |
| Stone observations | `prototype/body_localization.py` | Classical colour/body detection and conditional height correction |
| Local tracking | `prototype/continuous_tracker.py` | Simple same-colour image-space association; camera-local IDs |
| Throw events | `prototype/throw_detection.py` | Outgoing virtual-line crossings, not exact release instants |
| Experimental multi-layout routing | `prototype/layout_preflight.py`, `prototype/scripts/run_throw_pipeline.py` | Source-layout preflight and dispatch to the 2024 span or 2022 counter adapter; unknown layouts fail closed |
| Segment boundaries | `prototype/throw_segmentation.py` | Passage-to-next-passage review intervals and visible-stability candidates |
| Cross-view linkage | `prototype/cross_view.py` | Explicit coordinate transforms and unique receiving hog-line association |
| Evaluation | `prototype/stone_accuracy.py`, `prototype/pre_gate_geometry.py` | Detection matching, position discrepancies and straight-line residuals |
| Intent | `prototype/shot_intent.py` | Refuses to treat an aiming broom as a confirmed resting destination |
| Experiment scripts | `prototype/scripts/` | Source-specific processing, reports and browser checks |
| Historical upload indexer | `prototype/pipeline.py`, `prototype/server.py` | Coarse thumbnails and local upload/review |

Core detector versions and several historical geometry helpers remain byte-for-byte frozen so recorded fingerprints can still be verified. New orchestration, validation and handoff code is formatted. Standalone experiment scripts intentionally execute when run; import the core modules, not the scripts, from other code.

## Reproduce the latest experiment

This experiment uses the Canada–Korea composite recording, source interval 1650–2760 seconds. Source details and hashes are in `prototype/throw-analysis/source.json`; per-view landmarks are in `prototype/vision/annotations/calibration.json`. Source videos are separate from the code handoff.

1. `detect_throws.py` produces departure events from the full 360p recording.
2. `process_throw_segments.py` processes receiving windows from the 1080p end clip.
3. `process_departure_geometry.py` re-detects the saved departure observations at 1080p.
4. `build_throw_segments.py` and `build_cross_view.py` derive the review artifacts.
5. `render_cross_view_evidence.py` creates image comparisons.

Each command uses `feasibility/scripts/python.sh prototype/scripts/NAME.py`. The two processing scripts now validate cache fingerprints. Archived outputs from before that contract are **not silently reused**: use `--output /path/to/new/results --limit 1` for an isolated smoke run, or back up the experiment directory and use `--force` for a complete recomputation in its standard location. Report builders use the standard locations. Re-run `research/meeting/build_briefing.py` after updating results to embed demo data for offline viewing.

For the selected-frame benchmark, run `evaluate_stone_accuracy.py` then `evaluate_body_localization.py`. They verify the frozen benchmark inputs before inference. Do not overwrite the annotation protocol to make a failed check pass.

### Full isolated reproduction

The completed clean run reproduced the reported outcomes across 59 output files, with tiny numerical differences and no changed discrete decisions. All 94 tests and seven browser checks passed on its regenerated outputs. See [the full reproduction audit](../../validation/full-reproduction/README.md) for scope, differences and evidence.

With the saved project inputs present, use a **new environment** and a **nonexistent workspace directory outside this repository**:

```sh
python3.13 -m venv /tmp/curling-clean-env
/tmp/curling-clean-env/bin/python -m pip install -r requirements-lock.txt
# If Chromium is not already installed:
/tmp/curling-clean-env/bin/python -m playwright install chromium
CURLING_PYTHON=/tmp/curling-clean-env/bin/python feasibility/scripts/python.sh \
  scripts/reproduce.py --workdir /tmp/curling-clean-run
```

The runner copies the project, deletes the measured output files and both camera caches in that copy, rebuilds the experiments, compares detailed results with the original files, and runs the software/browser checks. It processes the full 18.5-minute interval for throw detection, each throw's receiving/departure windows, and all 2,700 frames of the 90-second projection clip. It does not infer every native-resolution frame of the full match.

Required inputs include exact video files, saved review/reference images, manual annotations, the diagram-coordinate CSV and frozen benchmark protocols. The recorded baseline outputs must also be present for comparison; the runner refuses to claim reproduction without them. These are experiment inputs, not automatically regenerated labels. Re-downloading a URL is not guaranteed to produce identical video bytes. The run records input hashes and package versions in `validation/full-reproduction/` and preserves the original project outputs.

Comparisons exclude explicitly listed runtime/cache provenance fields. Numerical comparison uses absolute and relative tolerances of `1e-9`; tiny fitting differences can therefore fail the strict comparison even when reported measurements agree. Such differences remain visible rather than silently increasing the tolerance. To inspect their magnitudes:

```sh
python scripts/describe_reproduction_drift.py /tmp/curling-clean-run \
  --output validation/full-reproduction/drift.json
```

## What the results establish

- 46/48 stones detected and 40/48 within 10 cm of diagram references on selected development frames.
- 16 departure passages found in one annotated end.
- 16 provisional two-view links on that same end, with explicit gaps.
- Camera intrinsics, feature height, rink orientation and panel timing still involve assumptions.
- The release point, full pre-release delivery, physical trajectory accuracy, complete throw endings and generalization to unseen videos remain unvalidated.

The latest cross-view rule was developed after inspecting this end, including T08. Its 16 proposed links are **not 100% independently measured identity accuracy**. Older READMEs and run logs document earlier milestones; the root report and audit identify the current scope.

## Sharing

`python scripts/package_code.py` creates `dist/curling-code.zip`: source, documentation and the small fixtures needed for unit tests. It excludes the Python environment, downloaded recordings, raw download metadata and generated experiment results. To run the demos or reproduce the original experiments, provide the separate project data folders as well. No project-wide license has been selected; third-party data/software retain their own terms.
