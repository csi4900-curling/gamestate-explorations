# Counter chronology as an ambiguity clue (development)

The broadcast shot counter is delayed, so its update time is useful evidence but not a physical release timestamp. This audit asks whether the *previous* counter update can distinguish two camera shots competing for the next counter. For each unlinked counter with multiple camera-shot options, an option survives when its origin probability is at least 0.2 and its shot ends at or after the previous counter update. The audit selects a shot only when exactly one option survives. It does not change any event ledger.

| Exposed recording | Ambiguous counters | Unique choices | Already linked shots ending before the previous update |
| --- | ---: | ---: | ---: |
| Switzerland 2022 | 2 | 0 | 1 |
| China 2022 | 3 | 1 | 3 |
| Slovakia 2022 | 4 | 1 | 2 |
| Canada–Norway 2022 | 1 | 1 | 0 |
| **Total** | **10** | **3** | **6** |

The three proposed choices are China B35 → S173, Slovakia B93 → S438, and Norway B69 → S389. China and Slovakia already had those shots linked in a separate visual-event branch; only the Norway association is new as a *proposal*. Source review of Norway B69 shows S387 with a yellow stone before the B68 yellow update, and S389 with a red delivery before the B69 red update. That visual review supports S389, but does not constitute an independent physical event label.

The six already linked counterexamples mean this chronological condition cannot be a hard event gate. Updates can lag a following delivery. All four recordings were already exposed to development, and the rule was proposed after inspecting Norway B69. The result is a diagnostic of competing shot assignments, not a transfer validation, precision/recall measurement, or proof of stone identity.

Reproduce from the project root with `python prototype/scripts/audit_2022_counter_chronology_tiebreak.py`. The frozen inputs, source hashes, per-option decisions, and code hashes are in [the machine-readable audit](pwg2022-counter-chronology-tiebreak-development.json).
