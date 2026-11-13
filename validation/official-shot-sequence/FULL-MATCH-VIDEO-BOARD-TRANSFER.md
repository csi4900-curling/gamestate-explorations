# Video board observations across a complete match

The [Canada–China 2022 full-match dashboard](../../prototype/full-match-canada-china/index.html)
now joins provisional throw-event review windows to source-video partial boards
and independently published post-shot diagrams. It does **not** fill missing
video states from the PDF or claim a continuous physical game state.

## Frozen source-only scan and first comparison

The [video-only scan](china-full-match-source-video-boards-first.json) sampled
all 116 readable broadcast-counter intervals in the 8,356-second Canada–China
source. It inspected frames at +4, +6, …, +30 seconds after each counter, but
stopped 12 seconds before the next counter. It accepted overhead geometry in
36 intervals and emitted stable partial boards in 28, containing 124 anonymous
stone observations. This file was written before loading official diagrams.
The two other previously emitted boards in the dashboard came from an earlier
targeted source-video audit where the full scan abstained; one earlier board
duplicates the new scan and is not counted twice. The dashboard therefore
shows 30 unique event-linked partial boards.

The [first postscore comparison](china-full-match-video-board-first-score.json)
withheld two ambiguous counter links. Of the 27 scored intervals with a video
board, 106 of 115 emitted stones matched same-colour official symbols within
0.25 house radii, and 16 boards matched the complete corresponding diagram.
The nine unmatched emitted stones and missing official symbols remain visible
in the per-counter rows. Five successive China end-three counters, B40–B44,
contain extra video stones against the PDF; this is a concrete target for
checking false caps, timing, orientation and diagram scope. The largest
distance among accepted matches was 0.1777 house radii. No physical metric
calibration or persistent stone identity was measured by this comparison.

A [six-frame mismatch audit](china-board-mismatch-audit.png) marks the
unmatched video detections at B40–B44 and B47, with
[source-time provenance](china-board-mismatch-audit.json). The B40–B44
mark is a visible stone near the lower ring edge, repeatedly present while
the official diagrams omit it. Its in-play status and the diagram's scope
need direct adjudication; it should not be labelled a detector false positive
merely because it is absent from the PDF. At B47, one marked yellow
detection lies on the side walkway near a person, and the overhead view crops
the far sheet. That case shows why a complete ring alone does not guarantee
complete board coverage or a stone-only field of view. The marked stills
were prepared after scoring and do not enter the source-only detector.

This is a development-source comparison using broadcast-counter order as a
shot-link proxy. There are 125 official shots, 125 provisional event candidates,
114 counter-to-official-shot proxy links, and only 30 video board links. Equal
event and shot totals do not establish event F1. Camera coverage and unreadable
counter intervals leave most shots without a usable observed board.

## Camera field-of-view audit

A separate [source-only image-coverage audit](event-gated-overhead-image-coverage-first.json)
computed the visible pixel bounds in detected house-radius coordinates for
every sampled overhead frame with a stable event-gated board. It used two
diagnostic rectangles: the house itself (±1 radius on both axes), and an
extended view (±1.25 laterally, −3 to +1 longitudinally). These rectangles
are visibility tests, **not** official in-play boundaries. The rectangular
image bound is optimistic because the actual sheet may be cropped by
walkways, people, graphics or another camera angle.

Of the 59 China board intervals, 39 had at least one frame whose image bounds
contained the whole house rectangle; **none** contained the extended
rectangle. Of the 13 Norway intervals, five contained the house rectangle
and **none** the extended rectangle. For example, China B47's observed
longitudinal range reached only about −2.84 house radii on the far side,
while the diagnostic extended view requires −3. A failed bound proves the
selected overhead image cannot show that entire area. A passed image bound
would still not prove that stones are visible or in play. These results
explain why even the 35 China and 11 Norway exact PDF-board matches are
*postscore agreement*, not video-only proof of complete game state.

## Wider timing probe (not promoted)

The first scan starts four seconds after the broadcast counter changes. A
separate [source-only timing probe](china-full-match-pre-counter-board-probe-first.json)
sampled from 24 seconds before to 30 seconds after each change, at two-second
intervals. It still bounded each search by the preceding counter plus 12
seconds and the following counter minus 12 seconds. This produced stable
partial boards in 60 of 116 intervals (206 anonymous stones), compared with
28 intervals in the first scan. No official board positions entered this scan.

The frozen [postscore diagnostic](china-full-match-pre-counter-board-first-score.json)
withheld two ambiguous counter links. For the 58 scored boards, 178 of 193
emitted stones matched the corresponding official symbols within 0.25 house
radii, and 34 boards matched completely. Comparison with the preceding
official diagram favored the current shot in 49 rows, tied in three, and
favored the preceding shot in two; four were the first shot of an end and
had no preceding diagram. In the two nominal preceding-shot wins (B88 and
B93), both diagrams matched the same four stones, and the mean-distance
advantage was only 0.0027 house radii. These are effectively
indistinguishable boards at this precision, not evidence of a clear
misassignment.

This comparison does not establish the exact time at which a photographed
board became settled. Official diagrams cannot be used to choose frames
without leaking the answer into the video detector. The wider-window boards
remain experimental and are **not** added to the dashboard's 30 video-state
links.

A further [source-only event-gated scan](china-full-match-event-gated-source-video-boards-first.json)
used the same wider offsets but required every sampled frame to occur at
least four seconds after its frozen provisional delivery-window end. It
emitted 59 stable partial boards containing 201 stones. The gate eliminated
B66, whose stable board appeared entirely before the event window ended,
and removed one early stone from B101. The
[first postscore comparison](china-full-match-event-gated-video-board-first-score.json)
withheld ambiguous counter links and scored 58 boards: 178 of 192 emitted
stones matched the current official diagrams, and 35 boards matched
completely. Among comparable prior/current diagrams, 47 favored the
current shot by match cardinality, seven tied, and none favored the prior
shot; four boards were the first shot of an end. This is stronger timing
evidence than the ungated probe, but the provisional delivery-window end
is not a measured settle time. These boards remain experimental and are
not promoted to confirmed after-throw states. A separate-recording transfer
follows below; direct review of ambiguous camera cuts remains necessary.

## Separate-match transfer

The same source-only temporal-board method was run on the complete,
counter-anchored second end of Canada–Norway 2022. Its
[frozen video scan](norway-end2-source-video-partial-boards-first.json) emitted
13 partial boards over 16 throws. In the
[first official-diagram comparison](norway-end2-video-board-first-score.json),
all 83 emitted stones matched, and 12 of 16 boards matched completely. This is
encouraging transfer evidence on a separate recording, limited to one selected
end. The end has counter-order anchors, not independently verified physical
throw times, and three shots still have no stable video board.

The unchanged China event-time gate was also applied to Norway end two in
a separate [source-only transfer](norway-end2-event-gated-source-video-boards-first.json):
13 of 16 shot intervals produced stable boards, containing 82 stones. In the
[frozen postscore comparison](norway-end2-event-gated-video-board-first-score.json),
all 82 stones matched the current official diagrams and 11 of 16 boards
matched completely. For the 13 observed boards, 11 favored the current
diagram by match cardinality, one tied, and the first shot had no preceding
diagram. The gate reduced completeness from the earlier ungated method but
did not eliminate the three uncovered shots. This transfer is a selected
end, so it does not establish a full-match game-state reconstruction rate.
The [provenance correction](EVENT-GATE-PROVENANCE-CORRECTION.md) documents
and preserves an earlier invalid Norway timing run; all figures above refer
to the rerun using Canada–Norway event windows.

## Video-derived state export

The [source-only state export](event-gated-video-state-observations-first.json)
lists all 125 provisional China events and all 16 selected Norway end-two
events. It attaches anonymous, unitless partial boards to 59 China and 13
Norway events and explicitly records missing boards for the other 66 and
three events. Every stone carries its source observation interval and an
`in_play_status` of unknown. The export also carries optimistic image-coverage
flags, unknown completeness, no measured settle time or persistent identity,
and `simulation_ready: false`. The event-level throw colour uses two agreeing
source-video release and receiving cues where available; this fills
VISUAL-S529's missing colour and corrects VISUAL-S593 from red to yellow,
while preserving the original labels. The
[source-frame audit](china-two-view-colour-revisions.png) and
[provenance](china-two-view-colour-revisions.json) show both revisions. No
official board positions enter the export or colour rule.
The export also carries each event's source-evidence tier, so a missing
video board on one of the four visual-only unconfirmed windows is not
mistaken for a confirmed throw with an unobserved outcome.

## Reproduction and next gate

The saved source media and counter files are required. First run
`prototype/scripts/scan_china_full_match_boards.py` or
`prototype/scripts/scan_norway_end2_boards.py` in a clean output location,
then score with their corresponding `score_*.py` scripts. The preserved
first-pass files refuse overwrites. Input and code hashes are recorded in each
output. Build the offline dashboard with
`prototype/scripts/build_full_match_canada_china_demo.py` and check it with
`prototype/scripts/check_full_match_canada_china_demo.py`.

For the event-gated branch, run the two `scan_*_event_gated_boards.py`
scripts, their matching `score_*_event_gated_boards.py` scripts, then
`audit_overhead_board_coverage.py` and
`export_event_gated_video_states.py`. Source-only scans and state export do
not read official diagrams; the two scoring scripts do.

The next game-state gate is complete video-derived board coverage, with
independent shot-time alignment and a measured 2D metric transform. A 3D rink
may visualize known board positions now, but a true replay and simulation also
need continuous trajectories, collisions, stone identities, spin and reliable
settling times.
