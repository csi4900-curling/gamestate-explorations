# Re-link delayed counters to existing visual events

The [reproducible replay](pwg2022-cap-visual-counter-links-development.json) applies the project's **existing** [following-view visual-link rule](../../prototype/counter_shot_alignment.py) to the current cap-fusion ledgers for three 2022 recordings. It first reproduces every baseline fused event exactly, then permits an unassociated delayed counter to attach to one otherwise unlinked visual-origin event when both cap and learned-box channels show the counter's colour immediately in the following shot. Ambiguous links abstain. The same [fusion rule](../../prototype/shot_event_fusion.py) preserves a wrong-colour origin as a conflict with `colour: null`; the counter never silently overwrites it.

| Recording | Event candidates before/after | Counter-linked before → after | New links | New colour conflicts | Counter gaps after |
| --- | ---: | ---: | ---: | ---: | ---: |
| Sweden–Switzerland | 115 → 115 | 93 → 96 | 3 | 2 | 7 |
| Canada–China | 112 → 112 | 92 → 104 | 12 | 10 | 12 |
| Slovakia–USA | 116 → 116 | 88 → 94 | 6 | 4 | 4 |

**Sixteen of the 21 new links** overlap the adjacent [travel proposals](CAP-FUSION-TRAVEL-RESCUE.md). This is a concrete way to avoid counting those travel observations as 16 entirely new throws. **Sixteen new event records expose colour conflicts** instead of hiding them behind a visual-only event and a separate counter gap. In China, B34 attaches to red `S169` while yellow motion appears in following `S170`; the resulting event colour is unresolved, not assigned yellow by fiat. B26 remains an unassociated counter with a separate yellow travel proposal in `S124`; its origin identity remains unknown.

The unchanged candidate counts are a bookkeeping property of this link operation, **not measured precision**. The two motion channels derive from the same frames, the learned scan selected shots using prior event and counter evidence, and adjacency does not prove one physical stone crossed the cut. All three recordings were exposed during development. The [travel/origin reconciliation](TRAVEL-ORIGIN-RECONCILIATION.md) remains a hypothesis audit, and no independent complete-video physical throw F1 or settled game-state transition is established.

Run `python prototype/scripts/replay_2022_cap_visual_counter_links.py` from the repository root to verify all three replayed ledgers byte-for-byte against the hashed source inputs and code. The 2022 baseline ledgers stay unchanged.
