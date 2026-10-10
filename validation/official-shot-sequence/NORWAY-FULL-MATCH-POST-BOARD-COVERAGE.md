# Norway full-match source-only post-candidate board scan

The [frozen scan](norway-full-candidate-post-window-source-boards-first.json) samples source frames after each of the 141 provisional Norway throw candidates. Its gate starts four seconds after the candidate window ends, samples every two seconds, and stops before the next candidate window. The official board diagrams do **not** select frames or stones.

The follow-up [camera-scoped image-coordinate scan](norway-full-candidate-post-window-image-boards-v2.json) keeps the same timing gate but groups accepted frames by broadcast camera shot and measures positions relative to each detected house. It never rotates uncertain images into canonical rink coordinates. This recovers partial boards from centred overhead views while keeping the reverse view separate.

| Coverage stage | Candidates |
|---|---:|
| Provisional candidate windows | 141 |
| At least one planned post-window sample | 129 |
| Accepted overhead house frame | 68 |
| At least one repeated stable stone observation | 47 |

| Camera-scoped image pass | Candidates |
|---|---:|
| Accepted overhead house frame | 107 |
| At least one repeated stable image-relative stone | 93 |

The second pass contains 367 stable image-relative stone observations in 101 camera-shot groups. Seventy-one of the 93 candidates have a counter link; 22 do not. The S281 post-cut camera shot S282 is among them: six sampled frames support a red position `(0.6410, 0.3397)` in image-house radii, with maximum within-track spread `0.0181` radii. Its orientation remains unknown to the general detector, as recorded in the output. The separate source review establishes the top-arrival direction for that one case.

The first pass's 47 partial boards contain 218 stable stone positions: 37 are after counter-linked candidates and 10 after counterless candidates. All counts here are **coverage**, not correctness or event recall. A board can be empty because the relevant view was absent, the timing gate was too narrow, or the stone detector had insufficient repeated support. A stable observed stone list is not proof that all stones on the sheet were seen.

The source has a real camera-orientation complication. Of the overhead frames where the existing detector could infer a delivery side, 350 read as top and four consecutive frames in S215 at 2970–2976 s read as bottom. The [2970 s source frame](norway-s215-2970-reverse-view.jpg) shows the house near the image top and the delivery stick entering from below. The scan therefore did **not** impose one global orientation. This conservatively leaves centred-house frames unresolved, including S281, although the separate [S281 source-only partial state](norway-e04-s12-partial-house-state-first.json) uses image-relative coordinates and has direct source-review support for top arrival.

The image-coordinate pass addresses the camera grouping and unknown-orientation issue. A [strict local motion audit](NORWAY-MOTION-APPROACH-ORIENTATION.md) proposes orientation for seven of 101 stable camera-shot groups, including three whose layout side was unknown; it abstains on the rest. A broader comparison still needs more reliable local orientation evidence. Assigning the majority orientation to all frames would invert valid reverse views. Candidate ordering also remains provisional: an unlisted true throw could contaminate a post-candidate board window. Neither scan establishes complete game state or simulation-ready geometry.

## Post-counter timing correction

The first retrospective [50-group diagram comparison](norway-full-known-orientation-image-board-postscore-first.json) is **invalid as a post-shot board score**: 33 groups contain source frames on both sides of the delayed counter decrement, and four groups are entirely before it. Some can show the previous shot's board. Retain it as a diagnostic of the timing failure, not an accuracy result.

The corrected [source-only v3 scan](norway-full-candidate-post-counter-image-boards-v3.json) requires counter-linked candidates' sampled frames to begin at least two seconds after their counter decrement and still stop before the next candidate starts. It leaves 46 of 99 counter-linked candidates with stable image-relative stones; the 42 counterless candidates retain the original source-only gate and 22 have stable stones. This timing rule is conservative and may discard real states; the counter is delayed delivery evidence, not a measured settle time.

The [post-counter diagram score](norway-full-post-counter-image-board-postscore-first.json) can compare 25 counter-linked candidates in 26 camera-shot groups where the house-position detector also provides an orientation. All 26 are top-labelled views. Their 99 observed stones match 99 same-colour PDF symbols within the existing 0.25-house-radius threshold; 24 groups have equal video and diagram symbol counts with all symbols matched. The other two each miss one diagram symbol. This is **conditional observed-stone agreement on a selected development subset**, not all-stone recall, independent physical-position accuracy, throw-event F1, or evidence that the remaining 74 counter-linked shots have correct boards. The camera-side label is a view-layout proxy; local motion and physical orientation still need independent checks.

## Longer-window sensitivity

The source-only [90-second horizon scan](norway-full-candidate-post-counter-long-window-boards-v4.json) keeps the same post-counter and next-candidate guards as v3 but permits more time to find a stable overhead view. Stable partial boards rise from **68 to 82 of 141 candidates**, with 14 gained and none lost. The [frozen comparison](norway-post-board-window-sensitivity-first.json) chooses each candidate's earliest scoreable camera group by **source time**, without using the official diagram to select it. On the selected development subset, the short horizon scores 25 candidates and 89/89 observed stones matched; the long horizon scores 34 candidates and 136/142 observed stones matched. Its six unmatched observed stones are in four eighth-end candidates (shots 10–13). Thus the longer window recovers coverage but does not preserve the shorter pass's perfect conditional agreement.

The longer pass is a sensitivity test, not a promoted production gate. A candidate ledger that misses a true throw can let the 90-second window include a later state even if it stops before the next *detected* candidate. A focused [eighth-end source-frame and residual audit](NORWAY-END8-FAR-HOUSE-GEOMETRY.md) found the mismatch concentrated in stones more than 1.5 house radii above the house, while visible boards stayed stable across sampled frames. That is evidence of a range-dependent coordinate discrepancy, not proof of its exact geometric cause or independent physical accuracy. Neither horizon establishes unseen-match accuracy or complete board state.

Reproduce with `feasibility/scripts/python.sh prototype/scripts/scan_norway_full_candidate_post_boards.py`, `feasibility/scripts/python.sh prototype/scripts/scan_norway_full_candidate_post_boards_v2.py`, `feasibility/scripts/python.sh prototype/scripts/scan_norway_full_candidate_post_boards_v3.py`, then `feasibility/scripts/python.sh prototype/scripts/score_norway_full_post_counter_image_boards.py`, after moving the frozen JSON outputs aside. The long-window experiment adds `scan_norway_full_candidate_post_boards_v4.py`, `score_norway_full_post_counter_long_window_boards.py`, and `compare_norway_post_board_windows.py` under `prototype/scripts/`. The outputs record video, candidate, counter, camera-shot, detector, stability, gate, comparator and runner hashes. The sampling gate, camera-cut isolation, board-state and comparator tests pass.

## One-second sampling and end-of-view evidence

The [dense source-only scan](norway-full-candidate-post-counter-dense-boards-v5.json)
keeps v4's 90-second horizon, delayed-counter guard and camera-shot grouping,
but samples every second. It finds a stable partial board after **88 of 141**
candidates, versus 82 in v4. It preserves all 432 stable image-relative stone
records and separately flags 425 whose last detection was within two seconds
of the last accepted frame in that camera shot. The flag is source evidence,
not a hard filter or proof of physical persistence after the cut.

The [retrospective v5 diagram comparison](norway-full-dense-board-postscore-v5.json)
finds 48 scoreable known-orientation camera groups: 207 of 219 dense-scan
observations match diagram symbols within the existing threshold, with 37
complete diagram-symbol matches. The terminal subset has 206 of 217 matched
and the same 37 complete groups. These are selected development comparisons,
not full-match precision or recall; groups absent from the video remain
unscored. Against v4's 41 common groups, dense sampling gains a matched
observation in one group but also adds unmatched observations in two.

The end-one shot-10 board is instructive. The 2-second scan missed a central
red stone because its detector found it in only two sampled frames. The dense
scan observes it in five one-second frames near the end of camera shot S54;
the terminal subset then has all five official diagram symbols. The dense
scan also retains an earlier short-lived yellow observation that the terminal
flag excludes. But applying that flag as a veto to the preceding shot-9
board would drop a red observation that **matches** its official diagram.
This counterexample prevents promoting terminal visibility to a general
hard rule. Neither example verifies physical stone identity or the candidate
event-to-shot association.

Reproduce v5 with `feasibility/scripts/python.sh prototype/scripts/scan_norway_full_candidate_post_boards_v5.py` and `feasibility/scripts/python.sh prototype/scripts/score_norway_dense_boards_v5.py` after moving their frozen outputs aside. Both artifacts record source and code hashes.
