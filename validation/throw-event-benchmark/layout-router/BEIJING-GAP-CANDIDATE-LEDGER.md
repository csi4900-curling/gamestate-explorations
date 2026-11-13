# Full-match Beijing 2022 candidate evidence across route gaps

The existing layout router emits partial throw-event timelines and explicitly marks unknown camera/layout intervals. Separate frozen counter-gap inventories found counter decrements inside some of those intervals; a Canada–China visual probe also found moving-stone pixels in one gap. The [gap-aware exporter](../../../prototype/scripts/export_beijing_gap_candidate_ledger.py) now places those saved signals into a source-ordered, hash-linked **candidate evidence ledger** while preserving every route gap and every original routed event ID. It does not promote gap evidence to confirmed throws.

| Full recording | Routed provisional events | Interior counter-gap candidates | Boundary-ambiguous counter transitions | Visual gap candidates | Ledger rows |
| --- | ---: | ---: | ---: | ---: | ---: |
| [Canada–China](full-china22-current-model/gap-aware-candidate-ledger.json) | 117 | 1 | 1 | 1 | 120 |
| [Slovakia–USA](slovakia-usa22-gap-transfer/gap-aware-candidate-ledger.json) | 95 | 3 | 2 | 0 | 100 |
| [Sweden–Switzerland](swiss22-gap-transfer/gap-aware-candidate-ledger.json) | 107 | 1 | 0 | 0 | 108 |

Canada–China's yellow counter update at 3662 s and yellow visual motion at 3668–3671 s appear as **two evidence rows** in the same 3600–3900 s unknown route. The visual row records the nearby counter ID but leaves physical identity unverified. Its separate red counter transition near 3629 s straddles the route boundary and is marked boundary-ambiguous; counting it as an additional throw could duplicate a routed event. The Slovakia and Swiss interior updates remain candidates with their counter evidence intervals and gap provenance; the previously prepared source sheets suggest stone movement in those areas but are not exhaustive truth.

The ledger solves an accounting problem: a downstream review or game-state process can now see these potential missed throws in sequence alongside supported-route candidates, with explicit `coverage_status` and source intervals. It does **not** solve segmentation recall, physical event boundaries, or game-state reconstruction. There are still unknown gaps with no counter evidence, and counters can be unreadable, wrong or delayed. No row has a verified distinct physical throw or a simulation-ready board. The full-match target still requires exhaustive independent event labels and complete video coverage.

The China visual probe was produced against the earlier partial timeline, while the current ledger uses the corrected monotone-counter timeline. The exporter verifies the visual probe's original timeline hash and checks that both timelines have identical source and route gaps before joining. All three ledgers record input, model and runner hashes. The [counter-gap inventory report](COUNTER-GAP-RESULTS.md) retains the original source-only evidence and limitations.
