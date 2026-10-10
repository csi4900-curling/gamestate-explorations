# Canada–Slovakia 2024: adjacent partial-board comparisons

The [partial-board audit](CANADA-SLOVAKIA-2024-POST-EVENT-BOARD-OBSERVATIONS.md) supplies 14 quiet-tail board observations after 17 provisionally accepted passages. The [comparison ledger](canada-slovakia-2024-adjacent-partial-board-comparisons-development.json) compares **adjacent accepted events only**. It attempts a comparison when both post-event boards were observed in the same receiving camera and no other passage candidate, including a withheld one, falls between their crossings.

| Result across 16 adjacent accepted-event pairs | Pairs |
| --- | ---: |
| Comparable partial boards | 8 |
| Abstain: missing quiet-tail board | 6 |
| Abstain: camera change | 1 |
| Abstain: intervening passage candidate | 1 |

The eight comparable pairs contain **16 conservative same-colour spatial associations**. Each pair of observations is within 0.25 m in *conditional camera-local coordinates*, and each observation must have exactly one nearby candidate on the other board. The output also records unmatched and ambiguous observations separately. For example, S13→S14 and S14→S15 each retain three associations, whereas S05→S06 has one retained association and one observation on each side without a nearby counterpart. Those unmatched detections are **not evidence of a physical stone appearing or disappearing**: occlusion, missed detection, displacement, and a false proposal remain possible.

This result adds a reproducible visual continuity signal to the video-to-state pipeline. It does **not** establish persistent stone identity, a complete board, a valid shot-by-shot state transition, end boundaries, score, or a simulator-ready state. The camera-local metric scale and association distance have not been independently validated. Crossing times are provisional, and a quiet-tail board is not proof of the exact settle time. The [implementation](../../prototype/adjacent_partial_board.py) and [runner](../../prototype/scripts/audit_adjacent_partial_boards.py) preserve these abstentions and all input/code hashes.

The next useful check is an independent post-shot board reference on a recording with known shot order and end boundaries. That would allow actual state-change accuracy to be scored; these associations alone cannot supply that score.

A [single evidence-state handoff](CANADA-SLOVAKIA-2024-EVIDENCE-STATE-HANDOFF.md) now joins the provisional passage, receiving path, partial post-event board, and this comparison into a candidate-ordered timeline. The comparison and board remain absent or unknown where their prerequisites fail.
