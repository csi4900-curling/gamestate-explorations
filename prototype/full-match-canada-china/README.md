# Canada–China 2022 full-match demonstration

Open [index.html](index.html) locally. It plays the complete 8,356-second source
recording and indexes 125 provisional event review windows. Use the event list
or timeline to seek through the match. The right panel shows all 125 official
post-shot diagram states as an **independent reference** and, where available,
the video-derived partial board linked to the selected event.

The [results.json](results.json) handoff records 33 unique source-scoped
release cues, five colour-concordant receiving observations, 30 linked
partial video boards, and 114 counter-to-official-shot *proxy* links. The
125 event proposals now expose evidence tiers: 116 have a broadcast-counter
anchor, five lack a counter but have a unique release cue plus same-colour
receiving observation, and four have only an unconfirmed visual window.
The [nine-event source-frame audit](../../validation/official-shot-sequence/china-counterless-event-audit/README.md)
shows the latter two groups without promoting the four weak windows to
verified throws. The
same frozen 1 Hz coloured-cap motion rule sees nearby stone-like tracks for
seven of the nine counterless proposals, including three of the four weak
windows. It misses VISUAL-S593 despite strong two-view release evidence, so
the motion result is shown as a diagnostic and is **not** a hard reject gate.
The [denser weak-window audit](../../validation/official-shot-sequence/china-counterless-event-audit/README.md)
records the frames and probe limits. The
two agreeing release/receiving colour cues fill one missing throw colour
(VISUAL-S529) and correct one conflicting provisional label (VISUAL-S593,
red to yellow). The original labels and cue provenance remain in each event;
the [source-frame audit](../../validation/official-shot-sequence/china-two-view-colour-revisions.png)
illustrates both cases. This colour correction does not establish persistent
stone identity across views. The
full-match source-only scan produced 28 stable boards from 116 readable
counter intervals; two earlier targeted boards add coverage where that scan
abstained. Its first postscore comparison covered 27 unambiguous boards:
106 of 115 emitted stones matched official symbols, and 16 boards were
complete. This is development evidence, not an independent full-match board
rate. There are
zero simulation-ready events. The equal totals of 125 proposals and 125
official shots are not a full-match precision, recall, or F1 result. The
review windows include broadcast context and waiting; they are not exact
physical throw boundaries. There is no reconstructed continuous trajectory
or measured stone rotation for this match.

The official boards are expressed in house-radius coordinates extracted from
the official PDF. Video boards are separately marked partial with unknown
metric scale and completeness. They are never filled with official diagram
positions in the runtime state. The counter link may attach a proposal to the
wrong physical shot even when its number and colour agree.

Build and check from the project root:

```sh
feasibility/scripts/python.sh prototype/scripts/build_full_match_canada_china_demo.py
feasibility/scripts/python.sh prototype/scripts/check_full_match_canada_china_demo.py
```

Inputs are the preserved v3 full-match event review and evidence handoff,
the frozen full-match source-only board scan and its separate postscore
comparison, source-linked targeted partial video boards, official shot ledger and diagram extract,
and broadcast-counter alignment. `results.json` carries input hashes. The
builder verifies the source video hash and refuses mismatched event joins.

The official ledger also records clockwise/counterclockwise turn direction
for 123 of the 125 shots. The viewer presents that as reference metadata,
separate from video evidence. It gives no revolution count or angular-speed
series.

The [perspective rink](rink-perspective.html) is an offline geometric
visualization of the same discrete board states, with a between-tee and a
house-close view. It lets the user step through all 125 official states, the
30 partial video boards frozen in the original demo, or a separate
[source-video event-gated export](../../validation/official-shot-sequence/event-gated-video-state-observations-first.json)
of all 125 provisional events. That experimental layer shows 59 partial
video boards and explicitly displays the 66 events without one. For each
observation it reports whether the frame bounds contain the whole house or
an extended diagnostic area; neither flag proves complete ice visibility.
Build its offline data module with
`feasibility/scripts/python.sh prototype/scripts/build_event_gated_perspective_data.py`.
The conversion from house-radius units to metres
uses the nominal house radius **for display only**. It does not interpolate
physical paths, establish a shared physical orientation across shots, simulate
impacts, or validate stone identities.

A 3D rink could visualize a known 2D state. A physical throw replay additionally
needs a verified stone identity across views, calibrated position through time,
orientation/spin observations, collision states and reliable settle times.
The center trajectory alone does not determine revolution count; a visible
handle or asymmetric marker must be tracked in the source frames.
