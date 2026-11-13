# One provisional event-evidence ledger across the 2022 recordings

The [reproducible union](pwg2022-provisional-event-evidence-union-development.json) combines four existing source-scoped outputs: re-linked visual-origin events, travel-view proposals, immediate-predecessor ambiguity, and held-origin proposals. It assigns **at most one event candidate per delayed counter**. Travel or held cues that share an already-linked counter become attached evidence on that candidate; they do not increment the event count. A travel cue that may be the same physical throw as an unlinked adjacent visual candidate remains unassigned until identity evidence can resolve it.

| Recording | Existing visual candidates | Union candidates | Counter-linked in union | Counter gaps left | Explicit colour conflicts |
| --- | ---: | ---: | ---: | ---: | ---: |
| Sweden–Switzerland | 115 | **117** | 98 | 5 | 2 |
| Canada–China | 112 | **123** | 115 | 1 | 10 |
| Slovakia–USA | 116 | **116** | 94 | 4 | 4 |

The China union contains ten new travel-only hypotheses and one held-origin-only hypothesis. B26 is a yellow **travel-only** candidate in `S124`; its origin and exact release remain unknown. B56 and B57 each have one travel candidate with a separate held-origin cue attached, so neither is counted twice. B22 has only a held-origin cue. B02 remains an unassigned readable counter. The Swiss B70 travel cue remains unassigned because more than one preceding visual origin may explain it. Every event retains source shot IDs, its evidence sources, colour/conflict status, broad delivery or travel windows, and explicit false flags for verified physical identity, settled-board transition and simulation readiness.

The union totals must **not** be scored as precision, recall or F1 by comparing them with official numbered shots. The official China total is 125, but a 123-candidate ledger could still have false positives and missed throws at the same time. The camera may omit releases, visual evidence can show displaced stones or equipment, and the counter can update before the receiving-view track starts. Candidate windows are not exact physical throw segments.

This is an integration milestone: downstream board-state code can consume one ledger with explicit evidence and abstentions while the detector research continues. It is not a validated complete-match segmentation pipeline or a simulation-ready state sequence. Run `python prototype/scripts/export_2022_provisional_event_union.py` from the repository root to verify the JSON exactly against hashed inputs and code; the four source artifacts and original fused ledgers remain unchanged.
