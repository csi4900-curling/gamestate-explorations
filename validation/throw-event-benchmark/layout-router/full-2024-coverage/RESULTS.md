# Whole-recording 2024 layout coverage, development audit

A later [Latvia and Scotland full-source transfer](LATVIA-SCOTLAND-RESULTS.md)
keeps the same 90-second router and 2024 span/context adapter fixed. Latvia
has 72 accepted candidates against 96 nominal completed-end deliveries;
Scotland has 112 against 112, but its red/yellow counts disagree with the
normal 56/56 split and 540 seconds of interior live-match view are routed
unknown. These are count and coverage failures, not measured event F1.

A separate [short-gap bridge development replay](SHORT-GAP-BRIDGE-RESULTS.md)
recovers Scotland's six interior layout chunks as conditional split-view
coverage. It preserves all 112 old event candidates and surfaces ten new
**review** candidates, including source-visible stones and broom/player
motion. A late Estonia cleanup control emits one apparent broom event, so the
bridge is not promoted as a direct accepted-throw rule.

An exact-track [surrounding-motion transfer](TRACK-CONTEXT-TRANSFER-RESULTS.md)
reproduces all 194 Scotland and 119 Latvia raw proposals, then tests whether
the neighbourhood follows the tracked object or stays fixed on the ice. The
cue prioritizes review but fails as either a hard veto or a rescue: Latvia's
highest-comovement accepted cases include visible stones, while its two
isolated withheld cases follow people. No acceptance or F1 claim changes.

A [frozen public stone-box probe](PUBLIC-BOX-CROSSING-RESULTS.md) at those
source-reviewed crossings rejects selected player objects but misses five of
nine visible stones even with its better clip-trained model. Small 360p caps
often fail the initial colour proposal or the frozen appearance threshold.
The public box model is therefore not a safe hard event gate either.

A [source-activity audit](ACTIVE-STATIC-LEFT-RESULTS.md) finds a more basic
coverage failure: the Latvia left panel is visually static for 1655 seconds
and the Italy left view is empty/static for 365 seconds while their right
panels remain active. Both spans were routed as supported split-screen play,
and neither emitted a raw left-panel candidate. A separate overlay flags those
seconds as detector-unsupported without changing any existing event decision.
An [exploratory right-view motion probe](ACTIVE-STATIC-LEFT-RESULTS.md#first-right-view-motion-probe)
finds source-visible moving stones inside Latvia's blind interval, but also
player and identity-switch tracks. It is a recall proposal route, not accepted
throw segmentation.
A post-review [early right-view entry tier](ACTIVE-STATIC-LEFT-RESULTS.md#early-right-view-entry-tier)
retains eight short Latvia prefixes that visibly follow stones across a
y=250 image line; all 131 raw right tracks remain preserved, and no entry is
promoted to a verified throw.
The unchanged rule's [four-recording transfer](RIGHT-ENTRY-FIXED-TRANSFER-RESULTS.md)
adds 34 review prefixes. All 34 show short moving-stone paths in sampled
source frames, and the 26 Italy/Estonia/China entries align with earlier
same-colour coarse windows. The same tier has no counterpart for 26 other
coarse windows in those three intervals; it is neither a complete detector
nor an independent event-accuracy estimate.
A [line-free right-span fallback](RIGHT-SPAN-FALLBACK-RESULTS.md) applied to
the preserved raw tracks after the y=235 variant adds only one source-visible
stone prefix across Italy, Estonia and China. Twenty-two of 52 coarse windows
still lack either right prefix, directing the next recall work toward colour
proposal and short-track recovery rather than another entry-line adjustment.
A separate [faster bidirectional right-view probe](RIGHT-BIDIRECTIONAL-RESULTS.md)
recovers short moving-stone paths in 12 additional coarse windows by admitting
up to 40 px/s consecutive steps and both image travel directions. It also
matches one coarse window through a player path and emits two off-window
person paths; these development proposals need an object filter and independent
event labels before they can be accepted.
A [fixed ice-context transfer](RIGHT-ICE-CONTEXT-TRANSFER-RESULTS.md) on a
Canada–Slovakia clip reviewed all 16 new right-view prefixes before scoring:
13 moving-stone paths and three person/wheelchair paths. The frozen 0.25
threshold kept all 13 stones in its isolated-ice tier but also put **two
athlete-head paths** there. Surrounding ice alone cannot establish stone
identity; these remain review proposals, not accepted throws.
A [second below-point context cue](RIGHT-CONTEXT-PAIR-RESULTS.md), developed
after those failures, separates 73 selected moving-stone prefixes from 14
selected people/equipment prefixes across six exposed recordings when paired
with the original ring score. This is same-agent development fit on short
paths, not an independently measured throw classifier or event F1.
A [frozen Canada–USA right-context transfer](../../canada-usa-2024/RIGHT-CONTEXT-TRANSFER-RESULTS.md)
reviews all 16 proposals before scoring: 15 stone paths remain clear and one
wheelchair path is cluttered. The right proposal stage overlaps only 15 of
20 existing coarse windows. A separate post-score late-seed diagnostic adds
two clear stone paths, one identity-uncertain stone path and four nonstone or
mixed paths; it does not solve the remaining right-view coverage or establish
physical throw accuracy.
A later [post-score area-aware association diagnostic](../../canada-usa-2024/RIGHT-CONTEXT-TRANSFER-RESULTS.md#subsequent-area-aware-association-diagnostic)
identifies greedy colour-track switches at two missed USA windows. On that
exposed interval, 25 review proposals show stone pixels in all 20 same-agent
coarse windows, with three long-track identities uncertain and five separate
person paths. The 20-window overlap is in-sample, not event recall.
An [unchanged-rule Italy transfer](../../canada-italy/RIGHT-AREA-AWARE-TRANSFER-RESULTS.md)
reviews all 17 new proposals before context scoring: 13 short stone paths,
two identity-uncertain stone-pixel paths and two people paths. The paired
context cue flags both people; the revised proposal stage overlaps 15 of 17
same-agent coarse windows, up from 13 for the old bidirectional tier. It still
misses I04 and I16 and does not establish physical throw recall.
A later [post-score Italy gap-two diagnostic](../../canada-italy/RIGHT-AREA-AWARE-TRANSFER-RESULTS.md#post-score-two-second-gap-diagnostic)
recovers stone-pixel paths in I04 and I16, yielding 17/17 same-agent coarse
window overlap on that exposed clip. It also makes an I13 yellow track's
identity uncertain, so the longer gap is not promoted without transfer.
On [unchanged Estonia transfer](../../canada-estonia-2024/RIGHT-GAP2-TRANSFER-RESULTS.md),
the gap-two lane yields 15/17 coarse-window stone-pixel overlap and flags its
one reviewed person path. It misses E11, which the older lane had already
covered with a source-reviewed stone path. Their conditional union covers
16/17, leaving E15; the lanes must remain additive rather than replacing
one another.
A [post-score global frame-assignment probe](../../canada-estonia-2024/RIGHT-GAP2-TRANSFER-RESULTS.md#subsequent-global-assignment-diagnostic-and-e15-limit)
restores Estonia E11 and yields 16/17 source-reviewed stone-pixel window
overlap; E15 still lacks continuous colour observations. The unchanged
[Italy transfer](../../canada-italy/RIGHT-GLOBAL-ASSIGNMENT-TRANSFER-RESULTS.md)
keeps 17/17 coarse-window stone-pixel overlap with 15 short stone paths,
two identity-uncertain paths and two person paths. Both are development
evidence, not physical-event F1.
A later [full Canada–Czechia right-view pass](RIGHT-ENTRY-CZECH-FULL-RESULTS.md)
finds 40 short moving-stone paths and five player/wheelchair paths among 45
review prefixes. All 40 stone paths have distinct conditional earlier left
links; all five person paths lack them. The relaxed entry threshold adds six
stone paths and one person path. This is a development source review, not
full-match detector precision or recall.
The [camera-aware fusion replay](CAMERA-AWARE-RIGHT-FUSION-RESULTS.md) preserves
those 40 Czech cross-view corroborations and five unmatched reviews while
keeping eight Latvia right paths as right-only reviews inside its documented
left-camera freeze. It joins 35 Czech corroborations to partial boards but
accepts no new physical throws or simulation-ready state.
A [Latvia post-entry image audit](LATVIA-RIGHT-ONLY-PARTIAL-CAPS.md) records six
repeated camera-local colour-cap sets after those right-only entries and two
scene/player-motion abstentions. These are visible-object proposals, not complete or
calibrated stone boards.
The [painted-house transfer audit](CZECH-HOUSE-ALIGNMENT-TRANSFER.md) replays
Latvia's image-alignment guard at 45 Czech right-entry samples: 34 of 44
adjacent pairs pass and ten abstain, often when foreground objects occlude
the house. This constrains pixel comparisons; it does not verify physical
stone identity or camera pose throughout an event.
The [full Scotland right-view replay](RIGHT-ENTRY-SCOTLAND-FULL-RESULTS.md)
finds 44 review prefixes across the entire source: 33 conditional cross-view
links, eight right entries in routed left gaps, two unmatched with supported
left lookbacks, and one right entry whose earlier left lookback crosses a gap.
Source review of the 11 noncorroborated prefixes sees eight moving-stone
paths and three people/wheelchairs; these are development observations, not
independent physical throw labels.
The [Czechia full-match board-sampler transfer](RIGHT-ENTRY-CZECH-FULL-RESULTS.md#fixed-right-view-board-sampler-transfer)
finds stable image-cap sets after 32 of 45 right prefixes, including two
prefixes source-reviewed as people. Post-entry board visibility therefore
cannot validate a throw event; camera-local caps remain partial state evidence.
A later [bridged Scotland cross-view audit](RIGHT-ENTRY-SCOTLAND-FULL-RESULTS.md#development-check-of-a-possible-cross-view-filter)
finds five clear stone crossings linked to later right entries, four clear
non-stone crossings unlinked, and one linked occluded case among ten selected
new bridge candidates. Its 244 time-shift controls produce at most 13 links
against 41 on the real timeline; a colour swap produces one. These exposed
development checks support a review filter, not event F1 or verified stone
identity.
The [Scotland ordered evidence handoff](RIGHT-ENTRY-SCOTLAND-FULL-RESULTS.md#ordered-evidence-for-game-state-reconstruction)
retains all 125 left/right proposals, maps 74 renamed baseline IDs explicitly,
and leaves physical game state and simulation readiness unknown.
Its [fixed-rule right-view board transfer](RIGHT-ENTRY-SCOTLAND-FULL-RESULTS.md#post-entry-partial-image-boards)
finds stable colour-cap proposals after 37 of 44 right entries and 17
alignment-supported adjacent image comparisons. These are incomplete image
observations, not verified post-throw stone boards.

An aligned [1080p crossing comparison](HIGHRES-BOX-TRANSFER-RESULTS.md)
finds more visible colour detail but does not reliably recover the missed
stone boxes: the frozen clip model still misses Scotland S59 and loses its
360p positive at S63. Resolution alone does not justify a hard event gate.

The [plan](PLAN.md) fixed 90-second preflight chunks on Canada–China,
Canada–Italy and Canada–Estonia 2024 before inspecting their full-video
layout outputs. The original preflights left 527, 2,040 and 873 seconds
unknown, respectively. Source [Italy 720–840](italy-gap-review-720/sheet-01.jpg)
and [4590–4710](italy-gap-review-4590/sheet-01.jpg) contact sheets show
split-screen live play inside those gaps. The
[2880–3000 sheet](italy-gap-review-2880/sheet-01.jpg) shows the same
split-screen geometry during an apparent changeover. These are
model-selected development inspections, not event labels.

The [postscore router revision](../../../../prototype/layout_preflight.py)
addresses two concrete measurement failures. One false Beijing-counter
read no longer vetoes a chunk with a sustained split-screen signature
if that read occurs on a split-signature frame. A stricter pale/bright
left-panel check allows the right scoreboard's blue fraction to be as
low as 0.40, instead of the older 0.50 requirement. The original
preflights and the first [single-conflict replay](replay-estonia24.json)
remain preserved. The [version-2 replays](replay-v2-italy24.json) recompute
signatures from the saved frame measurements. Fresh video-decoded
preflights for China, Italy and Estonia exactly reproduce the version-2
chunk layouts and gaps.

| Full recording | Original unknown | Revised unknown | Revised unknown share |
| --- | ---: | ---: | ---: |
| Canada–USA 2024 | 353 s | 353 s | 4.1% |
| Canada–China 2024 | 527 s | 347 s | 4.2% |
| Canada–Italy 2024 | 2,040 s | 240 s | 2.9% |
| Canada–Estonia 2024 | 873 s | 243 s | 2.9% |
| Canada–China 2022 | 1,696 s | 1,696 s | 20.3% |
| Sweden–Switzerland 2022 | 1,134 s | 1,134 s | 14.7% |
| Slovakia–USA 2022 | 1,616 s | 1,616 s | 21.2% |

No sampled 2022 chunk was newly routed as a 2024 split view. The
revised Italy route supports 90–8100 and 8190–8280 seconds, leaving
0–90, 8100–8190 and 8280–8340 seconds unknown. The remaining gaps
still need source/play-phase review. Five-second source
[stills at 8100–8190](italy-remaining-8100/sheet-01.jpg) show players
clearing the ice after play; [8280–8340](italy-remaining-8280/sheet-01.jpg)
is credits. Those sparse stills cannot certify every gap frame as
throw-free. A supported 90-second layout block
can contain camera cuts or hidden deliveries; it is **not** continuous
throw coverage. No event accuracy or full-video F1 follows from this
routing audit.

The unchanged 2024 span/context adapter then ran over the revised Italy
supported runs. Its [partial timeline](new-preflight-italy24/timeline.json)
contains 109 observed events and retains all three gaps; one event is
within its 40-second run-boundary review band. It emitted no events in
the short 8190–8280 run. The recovered 720–990 and 4590–5040 spans
contain four and seven provisional events respectively, demonstrating
that the old unknown spans included active event evidence. All 17
timestamp/colour pairs inside the older 1650–2760 development interval
exactly reproduce its [preserved output](../../canada-italy/development-span-confirmed-v2.json).
The resumed pipeline verified and reused the saved preflight and adapter
artifacts. The 109 full-run events have no exhaustive reference and
cannot be called 109 true throws.

The unchanged adapter also produced [128 Estonia](new-preflight-estonia24/timeline.json)
and [131 China](new-preflight-china24/timeline.json) provisional events
in their supported runs. The 17 Estonia and 18 China timestamp/colour
pairs inside their respective preserved 1650–2760-second development
intervals are exact matches to the older outputs. One China event and
one Italy event require boundary review; Estonia has none under the
40-second rule. The residual Estonia 3870–3960-second gap shows apparent
[end cleanup and ice preparation](estonia-remaining-3870/sheet-01.jpg)
in sparse source stills. China's 7920–8177-second gap shows
[postgame activity and credits](china-remaining-7920/sheet-01.jpg).
Those observations are not exhaustive negative event references, so
the gaps remain explicit. These three full-run event counts are
development outputs, not confirmed throw totals or precision/recall
measurements.

A non-mutating [chronology audit](SEQUENCE-REVIEW.md) flags adjacent
same-colour events for source review. It found 8 such pairs in Italy, 12
in Estonia and 8 in China; five within 40 seconds in one supported run
were preselected for source-only contact sheets. The two-second sampling
leaves all five unresolved. No event was changed from these signals.

The 90-second preflight also has isolated split-signature failures *inside*
supported runs: 5 sampled seconds in China, 9 in Italy and 4 in Estonia.
The [China](china24-supported-signature-failures.jpg),
[Italy](italy24-supported-signature-failures.jpg) and
[Estonia](estonia24-supported-signature-failures.jpg) source montages show
mostly the expected split view with marginal image fractions, plus a black
right panel in one China frame and closing credits in late Italy/Estonia
frames. This prompted an event-time layout audit that decodes source frames
at each crossing time and one second before and after. All 131
[China](new-preflight-china24/event-layout-audit.json), 109
[Italy](new-preflight-italy24/event-layout-audit.json) and 128
[Estonia](new-preflight-estonia24/event-layout-audit.json) provisional
events matched the split signature in all three samples. This rules out
the specific failure of an event landing on a sampled black panel or credit
frame. It does **not** verify that any event is a real delivered stone, nor
that the supported runs contain every throw.

A later [fine source review](FINE-EVENT-REVIEW.md) of selected flagged events
found one real red delivery followed by a likely broom-triggered false red
event in Estonia. Two China red events likewise appear to come from moving
equipment or players rather than delivered red stones. A fourth high-lateral-
motion China event is a real red delivery, so a velocity-ratio veto would harm
recall. These are prediction-targeted development findings, not full-video F1
labels.

The follow-up [second-view motion probe](RECEIVING-MOTION-PROBE.md) records a
large receiving red-stone track for the two reviewed real events. It also shows
why a naive same-colour motion check is unsafe: Estonia's previous stone still
moves during a later false candidate, and China players entering the right view
produce many cap-like motion tracks. This is a development diagnostic, not a
promoted confirmation rule or an F1 improvement.

On the 13 previously source-first matched real throws, the same receiving-view
cap-track rule (at least seven observations and 30 px displacement) fired for
only 6, while also firing for 2 of the 3 likely false events. A looser rule
recovered 11 of 13 real throws but still fired for the same two false events.
The [probe](RECEIVING-MOTION-PROBE.md) therefore documents a failed feature
screen, not a measured precision/recall change. The current timelines remain
provisional and still require independent source-first evaluation.

## Later right-view colour proposal diagnostic

The 2024 Estonia [larger-cap audit](../../canada-estonia-2024/RIGHT-GAP2-TRANSFER-RESULTS.md#subsequent-larger-cap-proposal-diagnostic) identified a concrete E15 miss: its visible yellow cap repeatedly exceeded the old 120 px² contour limit. A post-score 180 px² proposal lane recovered a short source-visible E15 stone path; its reviewed stone-pixel passage times overlap all 17 Estonia coarse delivery windows, versus 16/17 under the earlier global-assignment lane. The unchanged-rule [Italy transfer](../../canada-italy/RIGHT-LARGE-CAP-TRANSFER-RESULTS.md) emitted 19 paths, kept both person paths in the cluttered tier, and retained stone-pixel overlap in all 17 Italy coarse windows. These are development proposal and context findings. They have not been merged into the full-run timelines above, and they do not measure physical throw F1 or complete game state.

A provenance-checked cross-view evidence overlay now keeps the larger-cap paths alongside the **unchanged** full-match timelines: [Estonia](../../canada-estonia-2024/right-large-cap-full-timeline-overlay.json) has 13 unique short-stone time/colour links and [Italy](../../canada-italy/right-large-cap-full-timeline-overlay.json) has 15, using a declared 0–20 s right-after-left window. Long tracks and person paths remain unresolved. The overlays preserve all proposals and leave the original 128/109 provisional-event counts intact; temporal corroboration is not physical stone identity or a verified game state.

A later moving-tail diagnostic trims the long stationary-plus-moving right tracks and tests both passage orderings. The [Estonia](../../canada-estonia-2024/right-large-cap-motion-tail-timeline-overlay.json) and [Italy](../../canada-italy/right-large-cap-motion-tail-timeline-overlay.json) overlays each have 17 unique, source-reviewed **short stone-pixel** time/colour links to their 17 provisional left events in the 1650–2760 s development interval. All person paths remain unlinked and cluttered by paired context. The moving-tail rule was devised after inspecting both recordings' track timing, so this is exposed development evidence only; it does not establish full-match completeness or throw F1. The earlier overlays remain preserved as baseline artifacts.

The larger-cap/moving-tail proposal lane was then scanned over both routed Estonia split-view runs. Its [full-match audit](../../canada-estonia-2024/RIGHT-LARGE-CAP-FULL-MATCH-RESULTS.md) retains 152 right proposals beside the unchanged 128 provisional left events, covering 8190 of 8433 source seconds and leaving 243 s as explicit gaps. There are 124 unique time/colour candidate links, 28 right-only paths and four left-only events. Source review of the disagreements found four right-only moving-stone paths, 23 person/equipment paths, one person-handled stone, and four likely false left pixel paths. The context cue flags all 23 right-only people but leaves the person-handled stone clear; two time-matched yet cluttered right paths also visibly follow people. These are same-agent development findings, not physical event counts or F1.

The unchanged-rule [Italy full-match transfer](../../canada-italy/RIGHT-LARGE-CAP-FULL-MATCH-TRANSFER-RESULTS.md) retains 135 right proposals beside 109 provisional left events across 8100 routed seconds, with 240 s of explicit layout gaps. Its temporal inventory has 101 one-to-one candidate links, four right paths competing for two left events, 30 right-only paths, and six left-only events. Source review found eight moving-stone paths and 22 person/equipment paths among right-only proposals, while all six left-only pixels appeared to follow moving stones. A post-review targeted relaxed raw-track probe found stone-motion candidates for five of those six left-only events, but one path has uncertain identity and the sixth has no nearby same-colour raw track. Neither transfer is an independent throw benchmark, and the scans have not been promoted to physical event or game-state truth.

Provenance-checked candidate sequences now retain every left proposal, right path, source-reviewed disagreement and routed gap for [Italy](../../canada-italy/right-large-cap-full-candidate-evidence-sequence-v2.json) and [Estonia](../../canada-estonia-2024/right-large-cap-full-candidate-evidence-sequence-v2.json). A fixed three-frame split-view cap sampler then produced [Italy](../../canada-italy/right-large-cap-full-candidate-partial-state-sequence.json) and [Estonia](../../canada-estonia-2024/right-large-cap-full-candidate-partial-state-sequence.json) partial post-candidate observations. Respectively 73/109 and 74/128 provisional left rows have one or more stable right-panel colour-cap proposals; scene/player-motion and next-event windows abstain explicitly. These are partial image observations, not complete settled boards, and their sequence rows continue to mark simulation state unknown.

Fixed pre-event windows and conservative image-coordinate comparisons now extend those handoffs to [Italy](../../canada-italy/right-large-cap-full-candidate-pre-post-image-state-handoff.json) and [Estonia](../../canada-estonia-2024/right-large-cap-full-candidate-pre-post-image-state-handoff.json). Respectively 88/109 and 99/128 left candidates have comparable three-frame pre/post cap observations after window and scene guards. A time-spread Italy [source sample](../../canada-italy/right-large-cap-pre-post-delta-source-sample/sheet.jpg) also shows player/stone-handling overlap at several apparent changes. Thus appearance and disappearance are preserved as visibility evidence, not asserted physical board transitions or score changes.

The subsequent [ROI edge audit](../../canada-italy/EXPANDED-BOARD-CAP-ROI-RESULTS.md) found four Italy clear-tier false changes where a visibly stationary red stone lay on the cap sampler's upper boundary. Expanding the crop upward retains that stone in both windows but increases cluttered image-change proposals on both Italy and Estonia. This rules out treating the current clear-context cap changes as verified board transitions and motivates camera-specific house coverage plus occlusion handling.

A [source-derived right-house alignment audit](SPLIT-HOUSE-ALIGNMENT-RESULTS.md) now separates player occlusion from terminal credits at five-second source samples. It brackets the final split-to-credits cuts at 8263.5–8264.5 s in Italy and 8354.5–8355.5 s in Estonia. Source-reviewed, provenance-checked coverage overlays conservatively end routed support at 8264 and 8355 s; no provisional left event or right proposal falls in the removed tails. The latest candidate handoffs carry these refined gaps, while all throw and board claims remain provisional.

The [left-trigger coverage handoff](ACTIVE-STATIC-LEFT-RESULTS.md) additionally marks Italy's 365-second active static-left interval inside otherwise valid split-view layout. It preserves all candidates and shows one right-only path there; source review classified that path as person/equipment. This exposes a recall blind spot without asserting a missed throw count. Estonia has no such interval under the sampled audit.

A [lower-ice activity comparison](LEFT-BLIND-ICE-ACTIVITY-RESULTS.md) distinguishes the exposed Italy and Latvia blind intervals for next-step triage: sampled Italy lower ice is nearly still despite upper player motion, while Latvia has repeated lower-ice changes and source-visible stone tracks. Neither cue measures physical throw count or event F1.

A [source-first Latvia gap review](LATVIA-RESET-GAP-REVIEW.md) checks the separate 4279–4726 s accepted-event silence. The source shows a long house reset, and rejected motion near 4585–4587 s follows an athlete and attendant handling a stone. These raw paths must not be rescued as throws merely because they fall in a long candidate gap. The later 5003–6716 s silence contains eight distinct right-entry review proposals and remains a separate recall problem.

A [late right-track source audit](LATVIA-LATE-RIGHT-TRACK-FAILURE.md) finds that a lateral yellow cap shift near 5802–5805 s is an attendant pushing a stone with a broom, and ten later yellow raw tracks do not by themselves show delivered-stone passage. Loosening the right entry line or accepting lateral cap motion would therefore add known handling false positives without resolving the sixth-end coverage gap.

An [ordered full-match Latvia handoff](LATVIA-FULL-CANDIDATE-HANDOFF.md) now retains all 72 screened left passages, 47 left abstentions and eight right-only reviews in 127 time-ordered evidence rows, including the six available right-camera partial cap observations. Its 80 possible event proposals are not an 80-throw truth set, and all physical/game-state fields remain unknown. Source and intermediate artifact lineage are checked by the exporter.
