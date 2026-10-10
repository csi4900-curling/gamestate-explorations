# Accepted left passages without a right-camera proposal

Of the 72 provisional screened left passages in the full Latvia scan, **ten** have no compatible right proposal under the saved time, colour and direction join. The [source-pixel review packet](accepted-no-right-source-audit/manifest.json) pins the full 360p source frame and an enlarged marked crop for each crossing, with source, input, runner and image hashes. The review was selected after predictions were available and is **not independent throw labeling**.

| Marked source pixel | Candidate IDs | Count |
| --- | --- | ---: |
| Stone-shaped body with coloured cap | [S04](accepted-no-right-source-audit/S04.jpg), S49, S59, S67, S90, S104, S110, S114 | 8 |
| Person head | [S45](accepted-no-right-source-audit/S45.jpg) | 1 |
| Ambiguous yellow pixels beside a player | [S119](accepted-no-right-source-audit/S119.jpg) | 1 |

The eight stone-shaped crossings are already short moving-track observations in the left detector. A single marked frame does not prove a complete physical delivery or continuous identity, and the missing right proposal does not prove that the stone was absent from right-camera source pixels. It may reflect the proposal tracker, occlusion, camera geometry or broadcast timing. Conversely, S45 shows that an accepted left passage can follow a person. Thus **requiring a right-camera proposal as a hard event gate would lose at least these eight stone-pixel paths**, while keeping every unmatched left passage would preserve a known false candidate.

The [full-match development ledger](FULL-MATCH-AREA-CANDIDATE-UNION.md) attaches all ten findings without changing the original 72 accepted decisions. Its possible-event count is still a review count, not a verified throw count or F1. The next useful detector stage needs object identity evidence beyond one colour blob and an independent, exhaustive source reference to quantify precision and recall.

Reproduce with [`audit_latvia_accepted_no_right_source.py`](../../../prototype/scripts/audit_latvia_accepted_no_right_source.py), passing the frozen area-aware episode join, raw left screen and full 360p source. It decodes the exact source timestamps with FFmpeg, refuses overwrite, and records each marked card's SHA-256.
