# Frozen fourth-recording probe: Canada–Slovakia 2024

Recorded 8 October 2026 **before running the line-free candidate generator, 1080p receiver scan, or conditional dropout rescue on this interval**. Use the existing 360p full-match copy `validation/exploratory-transfer/canada-slovakia.mp4` (SHA-256 `154e2527ec8c5ea4f5cb38475d3a64c80f708776f2a696b8f284499619542e31`), source ID `DXM6bfHR4o8`, fixed source interval **1650–2760 s**. This recording was already inspected during an older, different throw-detector probe; it is not an unseen or independent test. The earlier probe identified two player-head false events near 1772 and 2647 s, but did not establish exhaustive throw recall. The reserved Canada–USA unseen end stays untouched.

Run the unchanged 2024 line-independent span detector at 10 Hz and the fixed left-panel corridor x=160±60 px to produce passage candidates. Preserve both raw and corridor outputs. Download a separate 1920×1080 copy of the same 1650–2760 s interval and verify source-time alignment before receiver inference. Then run candidate-centric 0.5 s / 12 s lookahead receiving motion with 160 px registration limit, conditional still-shot registration hold (10 s nearest eligible anchor), bounded gap selection (4.1 s; skip only registration abstentions), conditional cap-dropout rescue, frozen first/middle/last patch appearance, and shared timed-path deduplication. Preserve every stage and do not edit these rules after seeing this match's output.

There is **no exhaustive reference** for this interval. Report candidate and accepted-event counts, whether the two previously known player-head intervals generate or survive candidates, camera registration failures, and any obvious visual counterexamples. Do not report precision, recall, or F1 without a source-only event reference. Even if known false cases are rejected, that does not establish full-match segmentation. Source-only labels prepared later would be retrospective because this match was previously inspected; independent human labels on a different recording remain necessary.

Frozen fingerprints:

| Stage | SHA-256 |
| --- | --- |
| Span runner | `35f3062165aac099e9b9337fbd8305c2fc29032b5f1002` |
| Span model | `45a14f710e6523f1036f939b90fb196c0c6e7a636c47ab443000eb20340d42e4` |
| Stone-candidate baseline | `40678c23b117f527c80375ff7d7fbe3a1119fb94c4650b05698cd2c76be9628f` |
| Corridor runner | `d73c529bd32a8e68b45cc05021be2d0d68e50fed22bd8305c2fc29032b5f1002` |
| Corridor model | `3f8829d965d8a62312d9016e6955d1cc2c8546ad4e19c47b2d3c7a934f5bd036` |
| Candidate-centric runner | `77f9618344b41e773121e0348215206ecb7b6989fe7239f840e120428f612714` |
| Registration-hold runner | `10dc284a12da5858c4443339dabd65e53e197a9bd9a96df7208931e23542cc32` |
| Bounded-gap runner | `45ecb222ef75899326febfbae8a0e1c6aed5d3ffad04bf60408787e22a891b8c` |
| Rescue runner / core | `1b97fac7cf14a74307fefbd0e029e3b2be10b1023a55e8a8607c7eeb4b99d494` / `1e893842e9e57fa0e709cd5fddc375013f722f0fff7a20c7ccea26cbdc532918` |
| Patch runner / model | `716ae811e64566044b729883cb051bd757a8a1a8e7f5564b76b08ea72ae1c17d` / `10036a8b13e7e35f0be3cfd7280e9e0afaa3cf5b5da6cecc5623fb79695e0670` |
| Screen runner / core / dedup core | `ca5fe4e2c34fe3d372be46b0b327a7e2ae412c6885e214e786a5cdb7f6065c8e` / `e8a30d9408f29b4a01253107d09ba64685969aa1b244506fa94b6a6cfd0cd0ae` / `e43acfc10db0d0e4deaff578887244cbe51e1d08a2e7d7be8f44ad81bdde0c31` |

This same-production probe tests whether the fitted filter executes unchanged on another exposed recording and whether known person-motion false cases survive. It cannot establish cross-family robustness, high F1, exact release time, complete post-throw board states, or simulation readiness.

The [fixed-rule result](CANADA-SLOVAKIA-2024-DROPOUT-TRANSFER-RESULTS.md) retains 17/25 corridor candidates, but no exhaustive reference exists for precision or recall.
