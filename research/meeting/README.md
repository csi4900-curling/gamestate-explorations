> Current scope: one reliable left/right split-screen trajectory pipeline with stable stone identity and no manual per-video calibration. This document includes historical work. See [the current execution inventory](../../docs/CURRENT_PIPELINE.md) before using old commands or claims.

# Supervisor meeting reports

For the **Thursday 22 October 2026, 09:30** meeting, use the
[completed one-page handout](../../validation/meeting-2026-10-22/summary.html),
[printable PDF](../../supervisor-progress-2026-10-22.pdf), and
[detailed evidence appendix](../../validation/meeting-2026-10-22/index.html).
Both complete public-entry-point runs and the archived control/target comparison
are finished. Current Beijing event-context precision/recall is **88.9%/89.6%**,
not the historical adapter's 89.3%/100%. Processing took 120.4 minutes for Sweden 2024
and 132.2 minutes for Beijing. Current endpoint and viewer checks are linked in
these documents. Reliable complete-trajectory generalization remains unestablished.
The sections below preserve earlier development history and scopes.

The [transfer-video fit analysis](../../validation/TRANSFER_VIDEO_FIT_2026-10-20.md)
classifies the supported and failing video conditions, separating direct
2024-pipeline transfer from the separate Beijing 2022 adapter and learned
stone-box component. The 22 October brief links to this analysis.
The [fresh same-format transfer audit](../../validation/fresh-same-format-transfer-2026-10-21/RESULTS.md)
uses two further complete recordings selected before inference: a new 2024
split-screen match and a new Beijing 2022 match. It is the direct answer to
whether the system handles different videos in familiar formats. The separate
[three-match earlier first-run audit](../../validation/unseen-match-transfer-2026-10-21/RESULTS.md)
is retained as development history; those recordings were subsequently
inspected. The new Beijing match now has a [140-candidate source-video score](../../validation/fresh-same-format-transfer-2026-10-21/sweden22/SOURCE_VIDEO_REVIEW.md):
125 TP, 15 FP, 0 FN, event precision 89.3%, recall 100%, F1 94.3% after
same-agent review. The latest 2024 full source audit gives 140 TP, 7 FP and 3 FN (95.2% precision,
97.9% recall). The integrated pipeline and exhaustive projected-point scores are in the
[current viewer](../../validation/integrated-pipeline-final/index.html); earlier audits below retain their original scope.
The [full-match count audit](../../validation/full-match-count-audit-2026-10-20/RESULTS.md)
adds numerical precision and recall ceilings for four complete 2024 videos;
these are official-count constraints, not timestamped event F1 scores.
The [2022 official shot-list comparison](../../validation/full-match-official-comparison-2026-10-20/RESULTS.md)
reconciles 359 provisional candidates with 349 numbered official shots across
three complete development recordings: 344 matched events, 15 extra proposals,
and five missed shots (event F1 97.2%). The [per-event score](../../validation/full-match-official-comparison-2026-10-20/source-video-event-score.csv)
and [source-video review](../../validation/full-match-official-comparison-2026-10-20/SOURCE_VIDEO_REVIEW.md)
show the decisions and their limits. This retrospective score is separate from
held-out transfer accuracy and continuous physical stone tracking.

For the **9 October 2026, 10:00** meeting, open the concise
[French HTML brief](../../supervisor-progress-2026-10-09.html) or its
[PDF backup](../../supervisor-progress-2026-10-09.pdf). The
[English version](../../supervisor-progress-2026-10-09.en.html) has the same
content. Rebuild these presentation files with
`feasibility/scripts/python.sh research/meeting/build_demo_brief.py` and
reprint the French HTML to PDF. The HTML embeds the T11 figure; the interactive
demo links need the repository beside the report. The older
`build_progress_report.py` remains a deep research-report generator, not the
current presentation build.

Historical research notes below describe deeper material retained outside the
concise meeting brief.
It also links the new [two-stage throw audit](../../validation/two-stage-throw-audit/index.html):
raw proposals stay available when a filter withholds them. On the exposed
Estonia excerpt, one common image-context gate now retains three annotated
passages that the older speed gate removed. This is a development diagnostic,
not a new transfer score.
The Canada–Korea case study now includes a source-frame release-visibility
audit. The frozen tracks begin 0.3–1.5 seconds before the virtual line, but
T11's exact separation from the delivery device is occluded. The report and trajectory page
show first visible motion separately from the line crossing and retain an
unknown physical release time.
The meeting path now leads with the Canada–Korea 2024 end-three video used for
the earlier trajectory experiment: 16 internally annotated stone passages
matched one-to-one in that end, passage-to-passage review segments, and one
partial T11 receiving-view trajectory. Those segment boundaries are review
windows, not exact release-to-settle intervals; the trajectory comparison is
retrospective and does not measure physical position accuracy. The cross-match
results remain in the report to show how performance changes outside this
source-specific demonstration.
The French report now embeds a T11 two-camera trajectory figure built from
31 departure positions and 29 receiving positions, including 15 provisional
far-range receiving points. It shows the simultaneous 46.7 s endpoints and
their 0.61 m nominal longitudinal disagreement, links the interactive viewer,
and labels the cross-camera identity and geometry as provisional. Rebuild the figure from
`prototype/cross-view/results.json` with
`python research/meeting/build_t11_joined_figure.py`; the report builder
regenerates it automatically.
The targeted T11 audit expands the receiving-view projection range and finds a
candidate at the final departure timestamp. The earlier 5.8 s blank reflected
the bounded processing, not evidence of an invisible stone.
The report reads the frozen Canada–Norway first-transfer artifact and the
post-transfer spatial diagnostic. It also includes the public tracking clip
stone-box component comparison and the adjacent-view, mirrored-gate, and
held-origin and early-line first-transfer results through end eight. These are
explicitly separate from physical throw-event F1. The end-seven held-origin
transfer made no changes to the mirrored-gate decisions and matched 10 of 12
clean delayed counters; the end-eight transit-quality tie-break also made no
changes, while the gate matched 8 of 9 clean counters with one colour conflict.
The 8 October update adds a 359-candidate versus 349-official-shot sequence
diagnostic across three exposed 2022 recordings. With 275 clean counter anchors
fixed, 15 candidates are skipped and 10 official shots unmatched in every
lowest-cost alignment; these are review priorities, not measured false
positives or false negatives. The linked 25-case queue includes source-video
windows for skipped candidates and neighbouring windows for unmatched slots.
Four skipped candidates retain distinct source-video release cues, so the
sequence diagnostic cannot safely serve as a blanket candidate filter.
One tightly bracketed China end-one gap shows visible red receiving-view travel
after a cut that hides the release. The strict post-cut scanner accepts no
track there. This is a selected recall lead rather than a measured miss.
A selected China end-eight sensitivity check
finds yellow in both source-view cues for S593, which the event ledger colours
red. Changing that one colour lowers the sequence edit cost from eight to four
and aligns S593 to E08-S13. The frozen union remains unchanged, and physical
stone identity across the camera cut is unverified.
It also records the negative first cross-recording transfer of a non-origin
motion fallback and a five-shot camera-relative motion diagnostic; the fallback
remains unpromoted. A later postscore phase check removes three of four Swiss
fallback candidates and is labelled development, not validation.
The unchanged phase-aware fallback was then frozen and run across all 630 China
camera shots. Its two outputs duplicate existing event-ledger shot windows;
one conflicts with a linked yellow counter, so it remains unpromoted.
A selected camera-relative motion audit does not rescue those two outputs:
S123 has apparent movement relative to the camera without proving continuous
stone identity, while S519 has no reliable registration pair. This is a
postscore diagnostic, not an event accuracy result.
A follow-up selected track audit finds that one association jump accounts for
96.9% of S123's leading track path. It also finds possible internal view edits
below the frozen hard-cut threshold in both China candidate windows. Those
observations did not change the frozen event count or detector rules.
A selected Norway/Swiss comparison shows why a distributed-motion rule is
insufficient by itself: a Swiss camera pan also produces many moving image
steps, while camera-relative registration reveals little independent motion.
A frozen source-only scan then checked all 102 cap-corroborated China camera
windows. Its first audit had eight artificial track-link abstentions because
it replayed transit summaries through a second tracker. A corrected v2 keeps
the same windows, thresholds and transit summaries, and finds combined track
and camera-motion support in 15 windows; 42 have unknown visual colour and
abstain. A postscore counter-overlap check finds support in only 12 of 43
known-colour counter-associated windows. The report therefore rules out this
combined cue as a hard event filter; these are coverage counts, not physical
throw precision or recall.
An event-colour provenance export for all 112 existing China candidates shows
that 39 of the 42 visually ambiguous cap-motion candidates gain colour only
from a delayed counter, while three remain unresolved. Another ten candidate
colours are counter-derived without a corroborated visual candidate. The report
now makes that source distinction explicit for future game-state and coaching
work.
The latest full-source camera-boundary diagnostic reproduces all 629 China
and 603 Swiss conservative cuts, then proposes 58 and six additional possible
edits respectively. In China, 29 proposals fall inside existing same-shot cap
track intervals. The report embeds two before/after source examples. The
looser threshold also fires on non-cut visual changes in Swiss, so it has not
been promoted to a confirmed cut or event detector.
The existing background-registration test fails on all 64 proposed edit pairs,
including Swiss non-cuts, and therefore cannot serve as a cut verifier by
itself.
The same possible-edit scan, frozen after China/Swiss development, transfers
to full Norway and Slovakia sources with ten and 17 extra proposals. A frozen
temporal-isolation tier ranks seven and 13 as sharp spikes, but source review
finds real dissolves among the broad changes. Both transfer scans and tier
outputs reproduced exactly; neither rule is promoted as a confirmed cut
detector.
The China event grounding envelope combines colour provenance and tentative
camera-boundary risk for all 112 unchanged event candidates. Twenty-one have a
possible internal edit crossing a cap track; all remain explicitly not
simulation-ready. The report links this evidence handoff in its game-state
section.
An additional China source-scoped join checks eight earlier board windows
against that newer 112-candidate cap-fusion subset. Five windows have partial
boards; two of those five have no counterpart in the subset, including one
legacy event with a colour conflict. This is a coverage warning, not proof
that either physical throw was absent.
The report now notes a postscore held-cap-over-ice recovery proposal: it
recovers three counter-linked China candidates, including the B57 window with
a partial board, while proposing none in the Swiss or Slovakia transfers.
B26 remains unresolved by the held cue, and none of these proposals establishes physical F1.
The unchanged travel-view fallback, replayed on the three current cap-fusion
ledgers, proposes five Swiss, 21 China and three Slovakia counter-linked
travel observations. B26 gains a yellow receiving-view cue, but still has no
verified release identity or board transition. B56 and B57 overlap held-origin
proposals, so the lanes are not additive event counts.
The travel/origin reconciliation audit finds 17 of 29 travel proposals
immediately after an existing visual-only candidate; 13 pairs have conflicting
colours. The report treats these as duplicate/identity hypotheses, never
automatic event merges.
An unchanged one-to-one counter-link rule then attaches 21 counter updates to
existing cap-fusion events across the three recordings, including 16 of those
adjacent travel cases. Candidate counts remain 115, 112 and 116, while 16
colour conflicts become explicit. This is development provenance, not physical
event accuracy.
The new source-scoped provisional event union attaches duplicate travel and
held cues by counter and leaves ambiguous adjacent travel unassigned. It has
117 Swiss, 123 China and 116 Slovakia candidates. A China handoff now gives
all five selected partial-board windows a provisional counter-linked event;
only B26 has board frames overlapping an observed travel interval. No
physical stone-to-board transition is verified.
The report now links a full-match source-video viewer for all 356 provisional
event review windows. Search China B26 to show its camera switch and yellow
receiving-view track. The windows are bounded by source camera shots plus
context, not validated physical release or settle times.
A further source-visible ice-context tie-break chooses one of ten multi-option
counter abstentions on the three exposed 2022 recordings. Its frozen first
Norway transfer abstains on the only analogous ambiguity. The report keeps
this as a narrow view-context diagnostic, not a throw decision rule.
A subsequent chronology diagnostic proposes unique choices for three of ten
multi-option counters across four already exposed 2022 recordings, including
Norway B69. Six existing counter links violate its ordering condition, so the
report presents it as an ambiguity clue rather than a hard event rule.
An ordered-sequence audit proposes four of 11 ambiguous counter-shot links,
two of which would only attach counters to existing unlinked Slovakia visual
candidates. Source-frame review shows yellow handles in both of those Slovakia
shots, although the proposed counters are red. The frozen post-cut colour
audit independently calls S411 yellow and abstains on S372, so neither link
was added. A source-hashed colour-screen artifact now reproduces those statuses
without a manual join. The order audit also exposes three reversals among existing links.
The report keeps this as a review priority, not a validated correction or an
F1 gain.
A later postscore held-cap scan of all 13 shots offered by the ambiguous
Slovakia counters finds yellow caps in both disputed delivery windows, but also
detects a stationary red stone in an overhead view. It strengthens the colour
warning while showing why held colour alone cannot establish a throw.
The unchanged within-view held-to-motion cue fires in three of 13 ambiguous
Slovakia shots, including a yellow passage in S411 and a red passage in S374,
while abstaining on the stationary overhead S373. Raw red scoreboard counts
oscillate around B80/B81, so the report does not assign S374 to either counter.
A raw-counter support audit across all four exposed 2022 broadcasts finds that
only 58 of 400 emitted updates with visible readings on both sides meet a naive
0.75 exact-state threshold. The report therefore retains counter observations
as delayed, uncertain evidence rather than applying that threshold as a veto.
The unchanged held-to-motion cue was then scanned across all 116 provisional
Slovakia event windows. It yields one cue in 34, agrees with the ledger colour
in 30, conflicts in one house-side cluster, and has unknown ledger colour in
three. These are candidate coverage and internal consistency, not physical
throw precision or recall; none of the cue times is promoted as exact release.
The identical scan then transferred under a frozen plan to all Swiss and China
provisional windows: 46/117 and 31/123 unique cues, respectively. Across the
three recordings, the cue appears in 111/356 candidate windows. A source-only
join with the frozen strict post-cut colour sidecar finds 16 two-view colour
agreements, including four previously unknown ledger colours and the China
S593 red-ledger/yellow-source conflict. The colour correction remains
provisional; physical stone identity across cuts is not verified.
A temporal follow-up finds one same-colour receiving track in each of the 16
two-view cases, first seen 0.2–4.8 seconds after the cut, but the existing
background registration is unresolved in all 16. This supports temporal
compatibility without proving a continuous physical trajectory.
A selected China S593 feature audit shows why simply lowering the registration
threshold is unsafe: the unmasked fit has 11 inliers, but excluding the yellow
target leaves only seven tracked background features. The camera motion and
physical longitudinal trajectory remain unobserved in that view.
A source-scoped release-to-board join finds a unique provisional event via a
delayed counter for all nine partial boards. The historical broad-window scan
abstained on all nine. Rescanning China B57 within its attached held-origin
camera shot yields one red release cue at 3459.8 seconds, so one board now has
a provisional release-to-board evidence chain. Stone identity and the board
transition remain unverified. This is candidate-evidence coverage, not physical
throw recall.
The all-candidate shot-scope audit removes a Swiss B48 cue from an undeclared
camera shot and adds the B57 cue. It preserves 111/356 aggregate cues while
changing the recording split to 45 Swiss, 32 China and 34 Slovakia. The report
links the new provenance ledger.
An outside-union scan of 71 origin-predicted camera shots then finds three raw
held-to-motion passages. Two are ice-supported, source-visible delivery views
absent from the frozen 356-candidate union: Swiss S392 and China S216. A Swiss
close-up fails the ice check. An additive v2 candidate union includes the two
source-only rescues and the full-match viewer now shows 358 review windows;
the original 356-candidate union remains frozen. The new cases are recall
leads, not independently labeled throw true positives.
Both rescue cues have a verified cut followed by a unique strict red
receiving-view track, but camera-motion registration is unresolved and physical
identity is not verified.
The integrated v2 handoff now carries all 358 candidates with 113 unique
shot-scoped release cues, 18 two-view source-colour agreements, nine partial
board links, and one event with both a release cue and board link. All exact
physical release times, persistent stone IDs, settle times and continuous
trajectories remain unknown.
A complete scan of 1,351 camera shots outside the v2 union then found eight
raw held-to-motion triggers and four ice-supported triggers, all in shots the
origin model had rejected. Source review separates three Swiss precursor or
house-side cues from China S28, where the trigger is receiving travel rather
than a release. S28 follows an unassigned origin-like view and precedes raw
red counter B02; a postscore rule proposes one additional B02 event candidate
in an additive 359-event v3 union, preserving the frozen 358-event v2 union.
The report links source frames, the full-scan reconciliation, and the v3 viewer.
B02 adds receiving travel evidence but no visible release cue; the integrated
v3 handoff still has 113 release cues, 18 two-view colour agreements, and nine
partial-board links across 359 provisional candidates.
A counter-to-official-slot audit now shows why the 359/349 candidate/official
totals cannot be read as precision or recall: 308 counter-linked candidates
reach only 300 distinct official slots, 49 official slots lack a counter-linked
candidate, six slots receive multiple counters, and 51 video candidates have
no counter. China has exactly 125 candidates for 125 official shots but still
has 11 slots without a counter-linked event.
The state section now links a source-scoped provisional event-to-board handoff
for the original seven video-derived partial boards. A targeted Swiss end-two
extension adds two boards and two local adjacent-observation transitions, for
nine partial boards and 26 stone observations in the latest handoff. None is
simulation-ready.
The first same-rule adjacent-window transfer to Canada–China emitted two
partial boards from five shots and no complete boards; the report keeps this
coverage failure beside the favorable Swiss case.
The follow-up wide-view diagnostic shows three stable cap cues in the China
shot-12 window, but leaves them in image pixels because perspective geometry
has not been calibrated.
The simple ellipse-normalization diagnostic matches only one of three wide-view
stone positions within the board comparison tolerance, so those detections
remain image-space evidence.
The newer source-only grey-body estimator finds approximate ice-contact pixels
below all three caps in four wide frames. With a longitudinal flip indicated by
the shared yellow stone and a hypothesised 180-degree camera reversal, all
three contact positions match the official diagram in a selected postscore
check. Lateral orientation and perspective calibration remain unvalidated;
the report does not promote these points into the board export.
A selected adjacent-shot check found two stable red body contacts in a brief
wide view of China shot 11. Fusing them with its earlier one-stone overhead
observation matches all three official symbols in postscore comparison, but
inherits the unvalidated orientation and assumes a stable board between views.
This leaves the frozen five-shot first-transfer result unchanged.
The first source-only wide-contact scan on the other Swiss recording found
one stable contact where two stones were visible in its usable wide view.
That one same-colour overlap is compatible with both opposite camera
orientations, so the report keeps the wide-view path unpromoted.
After seeing that failure, a blue-ring-aware cap proposal recovers both Swiss
stones, but the symmetric same-colour board still fits both orientations.
A separately frozen five-window check on Slovakia finds no stable wide-contact
track because the sampled broadcast frames rarely show the wide house.
For the two selected China and Swiss handoffs, the asymmetric painted button
emblem supplies a source-only 180-degree camera-rotation cue in every sampled
frame pair. With that cue, one China and two Swiss wide contacts overlap their
earlier overhead observations. The provisional China union has three stones,
but no wide-view state is promoted into the main export or simulation.
A frozen coverage probe on 19 Norway end-eight delivery-view shots found no
accepted complete-house view in 57 sampled frames, so the emblem cue cannot
currently route the early throw detector. The report states this separately
from its selected board-view orientation result.
Rebuild it from the project root with
`python research/meeting/build_progress_report.py` after checking any new
evidence. The builder refuses changed headline metrics until the copy is
reviewed.

## Earlier briefing — 26 September 2026

Open `../../supervisor-briefing.html` in a browser. The briefing embeds its illustration, experimental image, comparison data, styles and scripts, so the main document works offline. Links to project reports require the surrounding repository; research links require internet access.

- Seven short sections organised around the requests, work performed and resulting findings, approximately 7–9 minutes plus discussion. The briefing is in French and contains no em dashes.
- **Speaker notes** / **N** exposes a suggested narration.
- **Large type** / **L** increases reading size.
- **Print / PDF** includes notes. `../../supervisor-briefing.pdf` is a generated backup.
- The oblique comparison uses actual t100 data from `prototype/body-localization/results.json`.
- Current evidence, implemented components and proposals are explicitly distinguished.
- Resources from the previous reuse proposal are integrated, with primary links and robustness limitations. Selected primary pages rechecked 25 September 2026: CurlObserver, Curlovision, PCN, Opening the House, IFCD, PnLCalib, ByteTrack and Ultralytics.

Rebuild from the project root:

```sh
feasibility/scripts/python.sh research/meeting/build_briefing.py
feasibility/scripts/python.sh research/meeting/check_briefing.py
```

The second command uses the existing local Playwright environment and Chromium installation, checks interactions and local links, captures screenshots and regenerates the PDF. See `browser-check.json` for results. No experimental inference code or benchmark results were changed for this document.

Linked demo JSON is embedded by `embed_demo_data.py` during report builds. Open the root HTML directly; keep the project folders and videos alongside it. No localhost server is required for these report demos. The upload slideshow is excluded from the main presentation. External research links still require internet; the IFCD publisher returned HTTP 403 to automated checks. See `link-check.json`.
