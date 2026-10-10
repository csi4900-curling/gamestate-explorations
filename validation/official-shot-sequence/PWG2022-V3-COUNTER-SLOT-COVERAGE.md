# V3 candidate count versus official shot slots

The [reproducible audit](pwg2022-v3-counter-slot-coverage-development.json) joins the additive 359-candidate event union to the existing delayed-counter alignment and the official numbered shot list. It uses the official list **only as a diagnostic reference**. The video detector does not receive official shot IDs or official timestamps.

| Recording | Provisional candidates | Official numbered shots | Counter-linked candidates | Distinct official slots reached by counters | Official slots without a counter-linked candidate | Slots reached by multiple counters |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Switzerland | 118 | 112 | 98 | 95 | 17 | 2 |
| China | 125 | 125 | 116 | 114 | 11 | 2 |
| Slovakia | 116 | 112 | 94 | 91 | 21 | 2 |
| **Total** | **359** | **349** | **308** | **300** | **49** | **6** |

China's **125 candidates for 125 official shots** illustrate why matching totals do not prove accuracy: its 116 counter-linked candidates reach 114 distinct official slots, two slots receive multiple counters, and 11 slots have no counter-linked candidate. The other nine China candidates lack a counter link. Across all three recordings, 51 provisional candidates have no counter link. China B02's new v3 candidate adds one distinct counter-anchored slot relative to the v2 union (113 → 114 China slots) and removes B02 from the unassigned-counter list.

An official slot without a counter-linked candidate is **not** a confirmed missed physical throw. Broadcast counters are delayed or unreadable, and an unlinked video candidate may correspond to that shot; the source-only China S216 and Swiss S392 leads show why this distinction matters. Likewise, multiple counters at one slot may be graphic flicker or alignment error rather than duplicate physical throws. A linked candidate is not verified physical identity merely because its colour and sequence slot match. The official pages do not provide video timestamps, so these numbers cannot be interpreted as physical throw precision, recall, or F1.

The audit exports every counter-linked candidate and its slot, all uncovered slot IDs, duplicate-slot groups, and per-end coverage for review. Run `python prototype/scripts/audit_pwg2022_v3_counter_slot_coverage.py` from the project root to verify the file against hashed union, counter-alignment, and official-reference inputs.
