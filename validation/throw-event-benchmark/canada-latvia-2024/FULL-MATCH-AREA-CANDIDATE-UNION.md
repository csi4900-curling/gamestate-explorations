# Canada–Latvia full-match candidate union

The [ordered development ledger](full-match-area-censored-candidate-handoff-development.json) adds the later 5670–6670 s [right-camera censored handoff](END6-FIELD-OF-VIEW-RESULTS.md) to the earlier [full-match left/right handoff](../layout-router/full-2024-coverage/LATVIA-FULL-CANDIDATE-HANDOFF.md). The two right-only sets do not overlap in time: the old eight entries are at 5067–5566 s; the newly source-reviewed area-aware entries are at 5671–6656 s. The exporter verifies both video fingerprints, both input artifacts, unique IDs, chronology, the static-left interval and a two-second nonduplication window against existing possible-event proposals.

| Evidence kind | Rows | Event interpretation |
| --- | ---: | --- |
| Screened left passage | 72 | Provisional; one known source-reviewed player path remains included |
| Left raw abstention | 47 | Preserved for review; excluded from possible-event count |
| Earlier right-only entry | 8 | Source-visible short stone-led prefixes; physical deliveries unverified |
| Later right-area moving-stone-pixel path | 16 | Same-agent source review; physical deliveries unverified |
| Later right-area person/clothing path | 4 | Preserved as nonthrow review evidence |
| **All ordered candidate rows** | **147** | Not a count of throws |

The review-tier possible-event count is **72 + 8 + 16 = 96**. This equals the *nominal* 96 deliveries for six completed ends, but it is **not evidence that segmentation is solved**. The existing screened left path **S45** follows player pixels in a source-targeted review; other screened paths are not exhaustively checked. The 47 abstentions could hide throws, right paths can switch objects or represent one physical event more than once, and the published end totals do not independently label video event times. No physical throw count, precision, recall or F1 is verified by this equality.

A [targeted source audit](WITHHELD-CROSS-VIEW-SOURCE-RESULTS.md) checks every withheld-left episode with a right-camera timing match. The only one-to-one pair, S76/A235, follows person/wheelchair pixels in both views. The other three groups contain clear people and ambiguous low red pixels. All eight left-side findings and their paired right-pixel classes are attached to the machine-readable ledger without changing any event decision.

The complementary [accepted-but-no-right audit](ACCEPTED-NO-RIGHT-SOURCE-RESULTS.md) checks all ten screened left passages without a compatible right proposal: eight have stone-shaped source pixels, S45 shows a person and S119 is ambiguous. These findings are also attached to the ledger. A right-camera match is therefore neither necessary nor sufficient for a confirmed physical throw in this recording.

A [crossing-shape audit](CROSSING-SHAPE-SOURCE-AUDIT.md) compares all 24 distinct source-reviewed left crossings with the detector's existing box and body-support measurements. Even thresholds chosen to retain every reviewed stone-shaped crossing leave three reviewed person crossings unflagged, so these measurements remain development features rather than a validated hard event filter.

The [patch-evidence-enriched ledger](full-match-area-censored-candidate-handoff-with-patch-evidence-development.json) attaches frozen crossing-local appearance scores to **13** source-reviewed accepted left rows. The [source-pixel probe](../../official-shot-sequence/LATVIA-ITALY-CROSSING-PATCH-SOURCE-CLASS-PROBE.md) shows why this is graded evidence: S45 person pixels score negative, but the visible stone paths S35 and S49 do too. The enriched ledger preserves all 147 rows, the 96 review-tier possible-event count, unknown verified physical throw count, and false simulation readiness. Reproduce it with [`export_latvia_crossing_patch_candidate_enrichment.py`](../../../prototype/scripts/export_latvia_crossing_patch_candidate_enrichment.py); the exporter verifies the packet, model, score and source lineage and refuses to overwrite its output.

A subsequent [all-accepted-left patch scan](ALL-ACCEPTED-LEFT-PATCH-RESULTS.md) scores all 72 screened left candidates with the same frozen model. Its five lowest-scoring previously unreviewed paths all show source-visible moving stone bodies, which reinforces that negative patch scores cannot be used as a hard nonthrow decision. The [all-left enriched ledger](full-match-area-censored-candidate-handoff-all-left-patch-evidence-development.json) attaches those 72 scores as graded evidence while preserving all original event and game-state claims; the 13-review ledger remains a narrower historical snapshot.

An [intermediate evidence ledger](full-match-area-censored-candidate-handoff-all-left-patch-and-source-development.json) also carries those five subsequent source reviews with their postscore origin marked. All 147 candidate rows remain, no new throw acceptance decision is made, and no complete post-throw game state is asserted.

The subsequent [complete negative-tier review](ALL-NEGATIVE-PATCH-SOURCE-RESULTS.md) checks all 34 model-negative accepted crossings, finding 32 stone-body crops, one person and one ambiguous case. Its [intermediate ledger](full-match-area-censored-candidate-handoff-all-negative-reviewed-development.json) makes no physical throw or game-state promotion.

The [all-accepted-left source-pixel review](ALL-ACCEPTED-LEFT-SOURCE-PIXEL-RESULTS.md) completes the other 38 crossings. Its [current evidence ledger](full-match-area-censored-candidate-handoff-all-accepted-left-source-reviewed-development.json) is the most complete version: 70 stone-body paths, one person path and one ambiguous path among the 72 accepted left proposals, with the 147-row union and all physical-event/game-state uncertainty preserved.

All 147 rows retain their evidence tier, source time, colour claim and ordering. The later 20 rows carry high-resolution moving-body pixels where available, a provisional one-second colour continuation, camera-boundary status and any later partial image board. None supplies a verified physical release or settle, a same-stone link into the board, a complete metric board, or a simulation-ready state. The source still has declared beginning/end routing gaps, and the static-left interval is only partially covered by source-reviewed right paths.

## End-five blind-interval gap candidate

A subsequent marker-conditioned sequence audit exposed an omission in this
**147-row handoff**, rather than a newly run detector. The seven screened
left candidates before the 5015 s freeze and the eight old right-only
entries through 5566 s form **15** review paths in the displayed fifth end.
Their colour sequence has two yellow entries in succession. The already
saved full-match area-aware right scan contains a separate **red** right-only
path, **R01:A367 at 5507.968 s**, between them. It was excluded because this
handoff imported area-aware right paths only from the later 5670–6670 s
interval. The [selected source strip](end5-gap-right-area-source-review/manifest.json)
shows a moving red stone at 5507, 5508 and 5510 s. The existing ring and
underpoint audit places A367 in clear-context review, with median non-ice
fractions **0.0171** and **0.0**. This is same-agent source evidence, not an
independently verified physical delivery.

The new [148-row ordered handoff](full-match-candidate-handoff-end5-gap-development.json)
adds A367 once at its source time, retains all 147 earlier rows and their
review decisions, and records its short 360p motion prefix with release,
settle, board and simulation state unknown. The review-tier possible-event
count rises from **96 to 97**; that does not imply an extra physical throw.
The older count's equality with a nominal six-end total was coincidental:
S45 is a source-reviewed person path, S119 is ambiguous, and neither the
new A367 nor the other proposals have independent exhaustive event labels.
The fifth-end *candidate* colours now alternate across 16 paths, which helps
prioritize review but cannot by itself validate any physical shot identity.
Reproduce this additive export with
[`export_latvia_end5_gap_candidate.py`](../../../prototype/scripts/export_latvia_end5_gap_candidate.py);
it checks the original handoff, full right scan, episode inventory, context
score and selected source strip hashes before writing a new versioned file.

## End-one blind-interval gap candidate and six-end sequence audit

Following the end-five recovery, [`audit_candidate_end_marker_counts.py`](../../../prototype/scripts/audit_candidate_end_marker_counts.py)
audited color alternation within stable broadcast end-marker intervals. In the first end (200–1050 s),
it surfaced two successive yellow proposals (`left:R01-S07` and `left:R01-S11`).
The full-match area-aware right scan contains an intervening red moving-stone path,
**`right_area:R01:A008`**, with clear-context review support and verified moving stone pixels.

The new [149-row ordered handoff](full-match-candidate-handoff-end1-end5-gaps-development.json)
adds A008 at its source time via [`export_latvia_end1_gap_candidate.py`](../../../prototype/scripts/export_latvia_end1_gap_candidate.py),
bringing review-tier possible events to 98 (with 149 total ordered rows).

Running [`audit_candidate_end_marker_counts.py`](../../../prototype/scripts/audit_candidate_end_marker_counts.py) produces:

| Broadcast end marker | Stable window (s) | Candidate proposals | Color sequence | Adjacent color violations |
| --- | ---: | ---: | --- | ---: |
| End 1 | 200–1050 | 15 | Alternating (Y/R) | 0 |
| End 2 | 1070–1900 | 16 | Alternating (Y/R) | 0 |
| End 3 | 1970–2800 | 16 | Alternating (Y/R) | 0 |
| End 4 | 2850–3800 | 16 | Alternating (Y/R) | 0 |
| End 5 | 3850–5570 | 16 | Alternating (Y/R) | 0 |
| End 6 | 5670–6670 | 17 | Alternating (Y/R) | 0 |
| **Total inside stable ends** | | **96** | **All 6 ends alternate** | **0** |

Across all six completed ends, the candidate total inside stable marker windows equals **96** (nominal 6×16 deliveries),
with **zero adjacent same-color violations across all 6 ends**.

As documented throughout, candidate count and color alternation are review heuristics rather than verified physical throw F1:
End 1 has 15 candidates (1 delivery unobserved), End 6 has 17 candidates (1 candidate is likely an extra object track such as S119),
S45 traces a player body, and physical stone identity across camera boundaries remains unverified.

Reproduce with [`export_latvia_full_area_censored_handoff.py`](../../../prototype/scripts/export_latvia_full_area_censored_handoff.py), passing the earlier full-match handoff, the later censored handoff, both source-audit manifests, the 360p full source and the 1080p 5670–6670 s excerpt. The output refuses overwrite and records all input, source-video and code hashes.
