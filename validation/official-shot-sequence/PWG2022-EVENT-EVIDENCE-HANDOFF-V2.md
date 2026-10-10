# Event evidence handoff, v2 source-rescue union

The [machine-readable handoff](pwg2022-event-evidence-handoff-v2-development.json) joins the additive 358-candidate event union to shot-scoped release cues, receiving-view colour observations, review windows, and video-derived partial boards. It preserves source and code hashes, exact input identities, and explicit uncertainty per event. The two source-only rescue candidates use their frozen outside-union origin scan and receiving-view audit. Existing events keep the earlier shot-scoped release decisions; no baseline event is re-scored.

| Recording | Provisional events | Unique release cues | Two-view source-colour agreements | Partial-board links |
| --- | ---: | ---: | ---: | ---: |
| Switzerland | 118 | 46 | 7 | 5 |
| China | 124 | 33 | 5 | 3 |
| Slovakia | 116 | 34 | 6 | 1 |
| **Total** | **358** | **113** | **18** | **9** |

The 113 cues are the prior 111 shot-scoped cues over the frozen 356-candidate baseline plus the two new source-only releases. The 18 two-view colour agreements are the prior 16 plus Swiss `SOURCE-S392` and China `SOURCE-S216`. They support candidate timing and colour, **not physical stone identity across a camera cut**. The nine board links use a delayed counter. Only China `TRAVEL-B57` has both a unique source-scoped release cue and a later partial board, and that link still does not verify which stone settled where.

Each record separates an approximate visible held-to-motion cue from `physical_release_time_s`, which remains null. Persistent stone ID, exact settle time, continuous trajectory, and simulation readiness also remain unknown or false for **all 358** events. This is a grounded input for later state reconstruction, not a completed game-state sequence or a physical throw-event F1 score.

Run `python prototype/scripts/export_pwg2022_event_evidence_handoff_v2.py` from the project root to verify the export against the hashed union, release, receiving, board, and review inputs. The join invariants are tested in `prototype/tests/test_event_evidence_handoff_v2.py`.
