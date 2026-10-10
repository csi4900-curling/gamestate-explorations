# Receiving-view travel proposals after cap-fusion abstention

The [cross-recording development audit](pwg2022-cap-fusion-travel-rescue-development.json) applies the **existing, unchanged** [travel-only fallback](../../prototype/counter_travel_fallback.py) to each recording's current cap-fusion ledger. For an unassociated delayed counter, it looks for same-colour cap and learned-box tracks in one otherwise unused camera shot near the counter update. A unique shot yields a provisional travel observation; no release-side stone identity is required or inferred. The learned-box scan covered selected shots, so an unscanned shot is not negative evidence.

| Recording | Baseline cap-fusion candidates | Unassociated counter updates | Unique travel proposals | Counter gaps left |
| --- | ---: | ---: | ---: | ---: |
| Sweden–Switzerland | 115 | 10 | **5** | 5 |
| Canada–China | 112 | 24 | **21** | 3 |
| Slovakia–USA | 116 | 10 | **3** | 7 |

These are **coverage proposals, not accepted throws or physical precision/recall**. Adding every proposal to the baselines would yield 120, 133 and 119 candidates, while the official numbered shot totals are 112, 125 and 112. The totals have different evidence bases and cannot by themselves identify false events, but they show why restoring counter coverage alone cannot be the precision gate. The Swiss audit also retains one counter with two possible travel shots as an abstention.

The China B26 case shows why the travel lane is useful yet limited. The old origin shot `S123` spans 1602.8–1611.8 s and includes a proposed internal camera edit at 1606.0 s. It has red motion evidence but no corroborated yellow origin. The following shot `S124` contains a yellow cap track from 1611.8–1617.4 s and a yellow learned-box track from 1611.8–1624.4 s; both overlap the source frames of a visibly moving yellow stone. The B26 counter changes at 1608.0 s, **before** the receiving-view track begins. The fallback therefore emits a yellow travel candidate for `S124` but leaves the release window broad, 1563.0–1608.0 s. It does not prove that any red object in `S123` is the same physical stone, or that the one visible yellow stone on the later partial board was delivered in this event.

The separate [held-origin lane](HELD-ORIGIN-COUNTER-RESCUE.md) proposes China B22, B56 and B57. B56 and B57 also have travel proposals, so the combined lanes cover **22 distinct** formerly unassociated China counters, not 24 separate new events. B26 is travel-only; B57 has both origin and travel cues, but their physical continuity across the camera cut remains unverified. All original ledgers are preserved unchanged.

The rule was run on exposed development sources and its two visual channels derive from the same frames. It does not establish independent full-match event F1, exact release timing, continuous trajectories, complete board transitions, or simulation-ready state. Run `python prototype/scripts/audit_2022_cap_fusion_travel_rescue.py` to reproduce the JSON exactly from hashed inputs.
