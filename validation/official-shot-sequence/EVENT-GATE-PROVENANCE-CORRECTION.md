# Event-gated board provenance correction

The first Norway end-two event-gated scan accidentally used delivery windows
from the Sweden–Switzerland recording. The source check was written as a
chained inequality, which did not reject a mismatched review hash when the
counter and video hashes agreed. Its derived first score and combined
image-coverage audit cannot substantiate a Norway timing transfer.

The original files remain preserved with `INVALID-wrong-review` in their
names:

- `norway-end2-event-gated-INVALID-wrong-review-source-video-boards.json`
- `norway-end2-event-gated-INVALID-wrong-review-score.json`
- `event-gated-overhead-image-coverage-INVALID-wrong-norway-review.json`

The Norway scan now reads `fused-linked.json` from the Canada–Norway full
transfer and requires its SHA-256, the counter source SHA-256, and the video
SHA-256 to be equal. All 16 selected counter IDs must have exactly one
Norway event window. The China scan's equivalent hash guard was corrected
as well. The prior China scan and derived files remain preserved with
`pre-provenance-fix` in their filenames; their stone results did not change.

The corrected first scans, scores, image-coverage audit and partial-state
export are the files without `INVALID` or `pre-provenance-fix` in their
names. The corrected Norway scan sampled fewer early frames in most
intervals. Its aggregate counts happen to remain 13 stable boards and 82
stones; the corrected postscore still reports 82 matches and 11 complete
diagram matches. Identical aggregate metrics do not make the invalid
timing source acceptable. The selected-end limitation remains.

The regression test `prototype/tests/test_event_gated_source_provenance.py`
deliberately supplies a review from another recording and verifies that
both scanners reject it before opening video.
