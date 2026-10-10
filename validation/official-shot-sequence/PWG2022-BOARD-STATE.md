# Official post-shot board-state reference

The [Beijing 2022 wheelchair curling results book](https://curlit.com/PDF/PWG2022_ResultsBook.pdf)
embeds one 300×600 diagram image for every numbered shot in the three
recorded session-one games. The [diagram extractor](../../prototype/scripts/extract_pwg2022_board_diagrams.py)
matches all **349 images** to the independent
[shot ledger](pwg2022-official-shot-ledger.json) by PDF page and position.
Each extracted image has a PDF image ID and SHA-256 in the
[diagram ledger](pwg2022-official-board-diagrams.json).

The diagrams alternate orientation: 192 put the house at image y=160 and 157
at y=440. The [stone parser](../../prototype/official_board_diagram.py)
detects the pink house location, finds small circular symbols, checks for a
filled red or yellow interior, and excludes the top/bottom stone racks and
thin outlined previous positions. It outputs image pixels plus unitless
positions relative to the outer house radius. This yields **1,328 coloured
symbols** over the 349 diagrams. No diagram exceeds the number of deliveries
so far in its end or eight stones of one colour; after excluding edge-adjacent
symbols, no successive diagram gains more than one stone.

The parser flags 26 diagrams for review: 21 have a symbol near a diagram
edge and six have a low fill margin, with one diagram in both groups. These
flags are retained in the [game-state reference](pwg2022-official-game-state-reference.json),
which joins each official delivery to its post-shot stone set and a reference
to the preceding shot's state. The states contain no inferred persistent stone
IDs, collision paths, video release times, physical metres, or 3D motion.
They are **official-diagram observations**, not reconstructed video states.

The two real-image parser fixtures cover an upper-house diagram with outlined
previous stones and a lower-house diagram with a stone on the button. Those
checks caught an initial orientation failure before the full extraction was
accepted. The source-linked state sequence can now test future video board
reconstruction and supply simulation inputs once diagram coordinates are
calibrated to rink dimensions and shot-to-video timing is established.

## First video-to-board check

The [source-video overhead detector](../../prototype/video_board_observation.py)
finds a blue house ring and coloured stone caps in 640×360 broadcast frames.
The [comparator](../../prototype/board_state_comparison.py) rotates the PDF
diagram when needed and matches same-colour positions in house-radius units.
At Canada–China video time 7110 s, corresponding to
`PREL000102-E07-S15`, it finds all ten stones (five of each colour). All ten
match the official diagram within 0.076 house radii; mean position difference
is 0.058 house radii. This is one selected clear frame, not a validation rate.

The first [three-game transfer audit](pwg2022-video-board-transfer.json)
uses five evenly spaced, counter-anchored shots per game. It samples frames
at +6, +12, +18, +24, and +30 seconds after the counter update and selects
the accepted overhead view with the strongest blue-ring support. The official
board positions play no part in that selection. Of 15 sampled shots, eight
had no confident overhead frame; seven were compared; **one of those seven**
had a complete stone match. The other six expose cropped or wrong house
geometry, person/graphic false caps, or missing stones. Counter time is only
an approximate shot anchor, so some selected frames may precede settling or
follow another shot. This audit is a development diagnostic, not held-out
board accuracy or throw-event F1.

The next revision needs temporal stability and multi-view coverage checks
before converting video detections into game states. Official diagrams
can then check the resulting board observations; they cannot supply the
release time or full stone trajectories by themselves.

### Conservative ring gate and field-of-view audit

A [second ring detector](../../prototype/video_board_observation_v2.py) uses
the connected blue-ring component and requires most angular bins to be
visible. It retains the same stone detector and the same 15-shot sampling
rule. Its [frozen transfer result](pwg2022-video-board-transfer-v2.json)
accepts five frames and completely matches three official boards. Two
accepted frames remain incomplete; ten shots have no accepted view. The
first audit above is preserved to show the coverage/quality tradeoff.

The [visibility audit](pwg2022-video-board-visibility.json) projects official
stone positions through each detected house into the video frame. Among 24
official symbols in the five accepted diagrams, six project outside the frame
or within ten pixels of an edge, and one in-frame symbol lacks a positional
match. For Slovakia–USA end 2 shot 15 specifically, five of the ten official
symbols are outside or near the frame edge and all five safely in-frame
symbols match. A close-up can therefore be a valid partial board observation
without being a complete game state. Projection is approximate and assumes
the house is circular in the broadcast view; it is not a measured board
recall estimate. Recovering full states from zoomed cameras requires stitching
observations across views or finding wider settled-board frames.

### Temporal partial boards

The [temporal board audit](pwg2022-temporal-partial-boards.json) samples the
same 15 counter anchors every two seconds from +4 to +30 seconds, stopping
12 seconds before the next counter observation. It carries the unanimous
delivery-side orientation from clear overhead views of each recording into
ambiguous zoomed views. A [stone clusterer](../../prototype/temporal_board_state.py)
emits a stone only after at least three detections spanning four seconds
within 0.10 house radii. This produces stable partial boards for seven shots:
22 emitted stones, all 22 matched to the official diagram within 0.25 house
radii; five of the seven boards are complete against the diagram. Nine shots
had at least one accepted overhead frame, but two had too few stable frames;
six shots had none. The remaining incomplete boards are kept as partial
observations rather than filled from the PDF.

The selection, orientation inference, and clustering use counter timing and
video pixels, not official board positions. The sample still depends on
development-source counter alignment, and its seven emitted boards are too
small and selected to establish cross-recording board precision or recall.
An adjacent throw could begin before the next counter update. Stable caps
from people or graphics remain possible. These observations carry colour,
unitless 2D position, time span, support count, and position spread, but no
physical scale, persistent stone identity, or reconstructed trajectory.

The [video-derived partial-board handoff](pwg2022-video-partial-board-observations.json)
exports those seven snapshots and 22 stones in a stable schema with source
hashes, observation intervals, unitless house-radius coordinates and support
counts. It deliberately omits official diagram positions and marks every
snapshot as incomplete/unknown and `simulation_ready: false`. The official
comparison can score an observation but cannot silently make the runtime
state complete. Metric calibration, persistent stone identities and verified
settle times are still required before these states can seed a physical
simulation or coaching claim.

### Targeted adjacent-board extension

A [source-only scan of five adjacent Swiss end-two shots](ADJACENT-BOARD-TRANSITIONS.md)
found stable two-stone boards after shots 12, 13, and 14; shots 10 and 11 had
no accepted overhead frames. The three emitted boards each completely match
their official diagrams in a separate postscore comparison. Two adjacent
partial-observation transitions are now exported without assigning physical
stone identity. The extended handoff has nine partial boards and 26 video
stone observations, all still marked not simulation-ready. The targeted
selection around a prior success is development evidence, not a new general
board detection rate.

The first [cross-recording adjacent-window transfer](CHINA-ADJACENT-BOARD-FIRST-TRANSFER.md)
used Canada–China end-two shots 10–14. It emitted two one-stone partial boards
from five shots; both emitted stones matched official symbols, but neither
board was complete. The transfer limits the Swiss case study: complete
adjacent boards depend strongly on camera coverage.

### Norway full-match diagram transitions

The [Norway transition ledger](norway-official-board-transitions.json), built by
[`build_official_board_transitions.py`](../../prototype/scripts/build_official_board_transitions.py),
compares each of the 128 official post-shot diagrams with its predecessor in
the same end. It pairs only same-colour symbols that have unique positions
within 0.05 house radii. Across the sequence, 314 symbol pairs meet this
coordinate-stability rule. Another 87 symbols from preceding diagrams and
132 from current diagrams remain unresolved; 118 shots have at least one
unresolved symbol. The 17 parser-flagged diagrams are retained in the ledger.

These are **diagram changes, not physical stone tracks**. An unresolved symbol
could represent a delivered stone, a displaced stone, one that left the
diagram's field of view, or an extraction error. A coordinate-stable symbol
need not be the same physical stone without stronger identity evidence. The
ledger supplies a complete shot-by-shot reference for assessing later
video-derived state changes while keeping those identities and dynamics open.

The [adjacent video-board audit](norway-adjacent-video-board-changes-first.json)
selects pairs using only consecutive shot slots and source-derived stable
boards with the same recognized `top` camera orientation. Eight pairs qualify
among the 120 within-end shot transitions. A 0.10-house-radius video
coordinate tolerance identifies uniquely colocated same-colour observations;
the official diagrams use 0.05. Six of the eight pairs have the same
colour-by-colour counts of stable, disappearing, and appearing symbols in
video and the official diagrams. Both disagreements are end-one pairs
9→10 and 10→11: the intermediate video board has one fewer red symbol than
the official diagram. The ledger retains the source intervals, symbols,
matches, and unresolved indices for review.

This is a selected, retrospective development comparison. It does not
establish complete video board recall, physical stone identity, or reliable
shot-to-video timing across the full match. The conservative unresolved sets
are suitable for a future game-state tracker that can carry uncertainty
instead of inventing stone trajectories between snapshots.
