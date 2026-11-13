# Public curling references for throw-event validation — 10 October 2026

We need an independent, exhaustive list of physical deliveries aligned to a
**continuous source recording**, including the intervals with no deliveries.
Only then can unmatched proposals count as false positives and missed throws
count as false negatives over the full recording.

| Source | What is published | What it can test here | Why it cannot establish full-match throw-event F1 |
| --- | --- | --- | --- |
| [CurlObserver dataset](https://github.com/CurlObserver/dataset/tree/2cfe61efede3c446957ee94aefa8df1345fc4684) | 5,000 detection images and 112 short tracking clips with per-frame stone boxes and track IDs | Stone appearance, box detection, and tracking on independently annotated positive clips | The clips were cropped around stone motion from throw to stop. They lack their parent full-match IDs and timestamps, continuous quiet intervals, and an exhaustive parent-match event ledger. Treating one clip as one throw would make recall trivial by construction and leave match-wide false positives unmeasured. |
| [CSAS 2026 data challenge](https://github.com/CSAS-Data-Challenge/2026) | Shot-indexed settled stone states and shot metadata | Game-state schema, shot order, and board-state logic | The published rows do not contain broadcast-video timestamps or source-video synchronization; see [state reference](../EXTERNAL-GAME-STATE-REFERENCE.md). |
| [Official Paralympic numbered-shot pages](../official-shot-sequence/README.md) | Ordered shot diagrams for specific 2022 matches | Shot-count and settled-board cross-checks for those matches | No source-video event timestamps; camera cuts and unobserved intervals still need alignment and review. |

The CurlObserver repository was checked at pinned commit
`2cfe61efede3c446957ee94aefa8df1345fc4684`. Its tracking directory has
112 video files and 112 corresponding per-frame label directories. For example,
`curling_vedio_0` has labels `00000000.txt` through `00000246.txt`; a row
contains class, normalized box coordinates, and track ID. The published
[README](https://github.com/CurlObserver/dataset/blob/2cfe61efede3c446957ee94aefa8df1345fc4684/README.md)
describes each clip as capturing stone motion from throw to stop. The labels
do not supply the enclosing broadcast's event timeline.

A targeted search found no public curling resource in this audit with both an
accessible continuous full-match video and independently annotated,
source-aligned throw boundaries. This is a finding about the inspected sources,
not a claim that no such dataset exists anywhere. We can continue to use the
CurlObserver boxes for the observation layer, and the official/CSAS records as
state constraints. None should be silently converted into an event-F1 ground
truth. For the acceptance gate, the outstanding input is an independent
source-aligned event ledger, whether from a publisher or a reviewer who has
not seen predictions. The ledger can be much lighter than stone-by-stone board
annotation: one marker per physical delivery plus coverage of the quiet
intervals is enough to score event precision and recall.
