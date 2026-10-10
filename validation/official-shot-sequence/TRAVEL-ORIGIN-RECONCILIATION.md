# Adjacent travel and origin evidence

The [source-scoped reconciliation audit](pwg2022-travel-origin-reconciliation-development.json) asks what would happen **before** the [travel proposals](CAP-FUSION-TRAVEL-RESCUE.md) were added to the event list. For each unique travel proposal, it inspects only the immediately preceding camera shot in that recording's frozen cap-fusion ledger. It preserves the origin candidate, travel cue and counter separately; it does not merge, suppress, or promote any event.

| Recording | Travel proposals | Adjacent visual-only candidate | Of those, colour conflicts | No adjacent fused event | Adjacent event has its own counter |
| --- | ---: | ---: | ---: | ---: | ---: |
| Sweden–Switzerland | 5 | 3 | 2 | 1 | 1 |
| Canada–China | 21 | 11 | 9 | 10 | 0 |
| Slovakia–USA | 3 | 3 | 2 | 0 | 0 |
| **Total** | **29** | **17** | **13** | **11** | **1** |

These 17 adjacent visual-only candidates may be the same physical deliveries as their neighboring travel cues. If every travel cue were counted as a separate throw, they are the main duplicate risk. Yet **13 of the 17 pairs disagree on colour**, so a same-colour-only merge would fail to resolve most of them. The China B34 example pairs a red visual-only `S169` with yellow travel in `S170` and a yellow delayed counter. That could be a wrong-colour visual cue followed by the delivered stone, or two distinct motions. The existing data do not prove which.

China B26 is different: no fused event exists in preceding `S123`, while `S124` has the provisional yellow travel cue. The older candidate ledger contains a colour-conflicted `S123` event, and the source frames show a camera change inside that shot; this audit keeps those outputs separate. China B57 likewise has no preceding *fused* event, although a separate held-origin cue exists in `S278`. Neither case gains verified cross-view identity from this adjacency check.

An automatic merge of all 17 pairs would reduce the hypothetical 29 new event IDs to 12, but this is **not an accepted count**: adjacency can join distinct throws, and a colour conflict is unresolved evidence. The actual cap-fusion and travel-proposal artifacts remain unchanged. Before turning this into a detector decision, the project needs a view-aware one-to-one assignment rule tested against independent complete-video throw labels. Run `python prototype/scripts/audit_2022_travel_origin_reconciliation.py` to verify the JSON exactly from hashed inputs.

The existing [one-to-one counter-link replay](CAP-VISUAL-COUNTER-RELINK.md) now attaches counters to 16 of these 17 adjacent visual candidates without creating new event IDs and retains their colour conflicts. It abstains on Swiss B70 because more than one visual-origin shot is eligible; adjacency to `S364` alone cannot safely settle that competition.
