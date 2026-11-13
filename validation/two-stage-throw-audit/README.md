# Two-stage throw-event development audit

Raw proposals are kept for recall. One image-context gate now runs over
all three frozen raw candidate lists; every withheld proposal remains reviewable.
China and Estonia were already exposed, so their new scores are post-score
development diagnostics. USA reproduces the frozen first transfer result.

| Recording | Proposal pool TP/FP/FN | Historical gate TP/FP/FN | Unified gate TP/FP/FN | Labelled throws in unified review |
| --- | ---: | ---: | ---: | ---: |
| canada-china-2024 | 17/9/1 | 17/4/1 | 17/1/1 | 0 |
| canada-estonia-2024 | 16/5/1 | 13/0/4 | 16/0/1 | 0 |
| canada-usa-2024 | 19/20/1 | 19/1/1 | 19/1/1 | 0 |

On Estonia, the spatial gate retained 16 reference matches, but the later
image-speed gate withheld three of them. The unified context gate restores
those three to the automated candidate set on this exposed excerpt. The raw
pool still misses one labelled delivery; a filter cannot
recover a throw that the proposal stage never produced.

The same context rule removes 19 unmatched USA raw proposals while retaining
its 19 temporal matches. On China it removes eight raw proposals, leaving
17 matches and one extra. These are exposed, partial-interval checks with
agent-made labels; they do not establish general precision or recall.

Next: broaden the proposal routes for occluded/cut deliveries, then freeze a
single confirmation policy and score it on independently labelled full videos.

Machine-readable candidate-level decisions: [results.json](results.json).
