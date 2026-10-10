# Norway end one: a 16-shot sequence hypothesis

The [machine-readable sequence](norway-end1-16-shot-sequence-hypothesis-first.json)
places the first end of Canada–Norway into **16 provisional video event
windows**. This is stronger than counting local motion tracks, but is still
a development hypothesis, not independently labelled throw-event F1 or exact
release/settle segmentation.

The first 15 broadcast-counter decrements (`B01`–`B15`) occur in order, and
their colours match the [official first-end shot order](pwg2022-canada-norway-official-ledger.json)
**15/15**. They link to 15 counter-backed candidate windows. The three
additional counterless candidate windows before the end transition are
`S40`, `S45`, and `S64`; each claims a global motion track also claimed by a
nearby counter-backed candidate. They are kept as duplicate-*review*
windows, not counted as new physical throws or declared definitively false.

The [unlinked-motion source audit](NORWAY-UNLINKED-MOTION-RESCUES.md)
surfaces a yellow delivery at origin shot `S86`, followed by yellow travel
in `S87` at 1203–1215 s. The official 16th shot is Norway/yellow. The
broadcast counter showed one yellow stone remaining before S86, then became
unreadable through the end reset; `B16` belongs to the next end. These
independent pieces make S86 a strong **provisional final-shot proposal**.
The exact release time, settled stone identity, and continuity through the
camera cut remain unverified.

The [official-board reference join](norway-end1-sequence-official-board-reference-first.json)
attaches the 16 independent PDF post-shot diagrams to the ordered video
hypothesis. It contains 69 extracted diagram symbols in total. This is a
review target for a future video-derived game-state pipeline, **not** a
video-observed game state or simulation input. The final diagram has a
low-fill extraction review flag, and all 16 rows explicitly say
`simulation_ready: false`.

The [source-only event-gated board scan](norway-end1-source-video-partial-boards-first.json)
then samples after each provisional event without consulting PDF positions.
It yields a stable **partial** board for 14/16 shots (none for shots 2 and 5),
with 57 emitted stone positions. The frozen
[postscore](norway-end1-video-board-first-score.json) matches 54/57 emitted
positions to the corresponding official diagram and finds seven complete
diagram-symbol matches. These figures describe detected positions in visible
views, not whole-sheet completeness or correct physical stone identities.

The final S86 row has only one stable video stone versus five official
symbols. The [source-only final-view audit](norway-end1-final-board-visibility-first.json)
finds overhead house frames only at 1221–1225 s before the camera leaves the
house. A yellow position hypothesis moves **2.014 house radii** between
1222 and 1225 s; the stone is not settled in the last available overhead
frame. The one stable observation resembles the prior diagram more than the
final diagram. This is an observation and timing limitation, not evidence
that the yellow delivery did not occur.

Reproduce from the frozen source ledgers and PDF extraction with:

```sh
feasibility/scripts/python.sh prototype/scripts/build_norway_end1_sequence_hypothesis.py
feasibility/scripts/python.sh prototype/scripts/attach_norway_end1_official_board_reference.py
feasibility/scripts/python.sh prototype/scripts/scan_norway_end1_sequence_video_boards.py
feasibility/scripts/python.sh prototype/scripts/score_norway_end1_sequence_video_boards.py
feasibility/scripts/python.sh prototype/scripts/audit_norway_end1_final_board_visibility.py
```

All outputs record input and code hashes and refuse overwrite. This first
end provides a concrete target for fuller source-only board reconstruction
and a way to distinguish genuine missing video coverage from event mistakes.
