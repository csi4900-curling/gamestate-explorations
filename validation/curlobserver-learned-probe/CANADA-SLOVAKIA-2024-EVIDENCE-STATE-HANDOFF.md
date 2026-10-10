# Canada–Slovakia 2024: video evidence to provisional state timeline

The [machine-readable handoff](canada-slovakia-2024-evidence-state-handoff-development.json) joins the frozen passage candidates, conditional receiving paths, [partial post-event boards](CANADA-SLOVAKIA-2024-POST-EVENT-BOARD-OBSERVATIONS.md), and [adjacent-board comparisons](CANADA-SLOVAKIA-2024-ADJACENT-PARTIAL-BOARDS.md) by candidate ID and source hashes. It gives downstream analysis one chronological record without treating a screen decision as an official shot or a partial board as a complete game state.

| Timeline status | Candidates |
| --- | ---: |
| Provisionally supported event, with receiving path | 17 |
| Screen abstention | 8 |
| Outside the screen corridor | 2 |
| **Total passage candidates** | **27** |

The 17 provisional events carry **247 observed receiving-path samples** in conditional camera-local ice coordinates. Fourteen have a partial stable post-event board; three explicitly lack a quiet-tail board. Eight adjacent accepted-event pairs have a camera-local comparison, and eight abstain. Every event retains its candidate colour and observed passage timestamp; `release_time_s`, `physical_settle_time_s`, `spin_revolution_count`, `end_identity`, and persistent physical throw identity remain unknown. Every timeline item has `simulation_ready: false`.

This is a **replay evidence contract**, not a physical replay. A visualizer can plot observed path samples and board detections in their own view-local coordinate frames, leaving gaps visible. It cannot yet render a defensible full throw or predict outcomes: the camera views are not metrically joined, the complete sheet is not observed, stone identities and end boundaries are unresolved, and event precision/recall against an exhaustive independent reference are unknown. The [exporter](../../prototype/scripts/export_slovakia_evidence_state_handoff.py) refuses a mismatched input-hash chain or conflicting candidate IDs.

The next validation gate is an independently referenced source with shot order, post-shot diagrams, and known end boundaries. Score event precision/recall, board completeness/position error, and cross-event identity separately before promoting any timeline row to simulation input.
