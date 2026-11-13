# Colour provenance in the full China event ledger

The frozen [export plan](event-colour-provenance-v1-plan.json) binds the existing [fused event ledger](fused-shot-candidates-replay-cap.json), its exact cap decisions, and the **same counter-alignment artifact used by that ledger**. An initial pre-output draft pointed to an earlier alignment file and failed the shot/counter consistency check. The plan records that correction; no partial export was written. The [provenance export](event-colour-provenance-v1.json) copies all 112 event identities, windows, colours and statuses unchanged, adding a `colour_provenance` object to each event.

| Colour basis | Events | Meaning |
| --- | ---: | --- |
| Unique visual colour and linked counter agree | 43 | Both pipeline channels support the same colour. The counter link itself requires adjacent same-colour motion, so these are not independent votes. |
| Visual colour only | 17 | One colour is supported by the cap-motion decision; no counter is linked. |
| Counter with ambiguous visual motion | 39 | Both red and yellow move in the adjacent-shot cap evidence; a delayed counter supplies the event colour. |
| Counter without corroborated visual candidate | 10 | A delayed counter supplies the colour on another event route. |
| Ambiguous visual motion, no counter | 3 | Colour remains unknown. |
| **Total** | **112** | **109 have a ledger colour; only 60 have a unique visual colour.** |

This explains the 42 unknown-colour abstentions in the separate [cap-track quality audit](../cap-patch-crossmatch-v1/CHINA-CAP-TRACK-QUALITY-FULL.md): they are **visual** ambiguities, not 42 unresolved colours in the fused ledger. Of those 42, 39 gain counter-derived colour downstream and three remain unknown. Counter-derived colour is useful game context but does not establish which physical stone was tracked through a camera cut or whether the candidate is a real throw.

Downstream game-state exports and future coaching prompts should carry `colour_provenance.basis` and `counter_is_delayed_proxy` alongside `colour`, and abstain from physical identity or trajectory claims when the source evidence does not support them. This enrichment is not an event detector change, an accuracy result, or a simulation-ready state. The export reproduces exactly from the frozen inputs and fails if its counter or cap dependency hash differs from the one recorded in the fused ledger.
