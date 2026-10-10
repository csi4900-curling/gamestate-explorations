# Corroborating a throw candidate across views: transfer boundary

The Czech [development corroboration replay](czech24-full-camera-motion-v1/dual-observer-corroboration-development.json)
flags a raw left candidate when a later right-view proposal has repeated
stone-like patches and a tightly overlapping high/low-resolution receiving
path. It flags 40 of 147 Czech raw candidates, including the two
[source-visible stones S04 and S13](czech24-full-camera-motion-v1/WITHHELD-STONE-SOURCE-REVIEW.md)
that the simple surrounding-motion gate withheld. It does not flag S96, a
source-reviewed non-stone raw path. The 40 flags are **supporting evidence**,
not 40 verified physical throws or an accuracy score.

The [Latvia full-match transfer audit](full-2024-coverage/latvia24-full-v1/context-rejection-source-review-transfer-development.json)
joins the current 119 raw / 72 context-confirmed pipeline run with the
existing source-pixel review ledger by exact source hash, candidate ID,
passage time, and colour. All 16 Latvia `large_surrounding_motion` rejections
have source reviews: 14 show person/equipment pixels at the tracked crossing,
and 2 remain ambiguous low red pixels near a wheelchair. No reviewed stone
track appears in this rejected group. This differs from Czech, where the
same gate rejected two source-visible stone tracks among 18 such rejections.

Latvia also supplies a recall warning against making right-view agreement
mandatory. Among its 72 context-confirmed left candidates, **10 had no
associated right proposal** in the historical handoff. Source review shows
stone-body pixels for **8** of these, person pixels for one, and an ambiguous
yellow path for one. A required right proposal would withhold those eight
source-visible stone paths. The Czech overlap rule itself cannot be replayed
unchanged on Latvia's current artifacts because they do not provide the same
per-left high/low-resolution receiving-path overlap field. The current
transfer therefore tests the *availability and meaning* of the evidence,
not that exact Czech rule's precision or recall.

The design consequence is an optional stone-specific corroboration branch:
positive right-view evidence can raise confidence or recover a left candidate
that a broad motion gate withheld; a missing right proposal must leave the
candidate unresolved rather than reject it. Both recordings were exposed in
development, share a 2024 broadcast family, and lack independent exhaustive
physical throw labels. The next validation must score a frozen branch on
another recording and separately verify physical identity through the camera
handoff. Post-event partial boards remain uncertain until stone identity,
settling, and board completeness are established.

The [Czech candidate-to-state union](czech24-full-camera-motion-v1/CANDIDATE-STATE-UNION.md)
now carries the recovered candidate evidence alongside old partial-board
episode references while preserving all raw and right-only proposals and
leaving complete physical game state unknown.

Reproduce the Latvia join with
`python prototype/scripts/audit_latvia_context_rejection_transfer.py`
after moving its output aside. It pins the reviewed source images, review
ledger, raw candidates, context decisions, and audit code by SHA-256.
