# Grounded event handoff for the China recording

The [frozen export plan](event-grounding-envelope-v1-plan.json) combines the unchanged [112 event candidates with colour provenance](event-colour-provenance-v1.json), the [possible-edit/cap-track overlap](possible-edit-event-overlap-postscan.json), and the [temporal edit tier](possible-edit-temporal-v1.json). The [event grounding envelope](event-grounding-envelope-v1.json) preserves every existing event ID, delivery window, resolved colour, counter link and evidence source. It adds only uncertainty metadata and a simulation handoff. The result reproduces exactly from hashed inputs.

| Camera continuity evidence | Event candidates |
| --- | ---: |
| A possible internal edit intersects a same-shot cap track | **21** |
| A possible internal edit, with no intersecting cap track | **14** |
| No internal edit proposed by this threshold | **77** |
| **Total** | **112** |

For example, `S36` carries a visually and counter-supported yellow colour, while a proposed edit at 473.6 s lies inside its same-shot cap-track interval. Its colour may be useful event context; the track has an unresolved camera-boundary identity risk. `S25` has a counter-derived colour because both visual cap colours were supported, and a possible edit at 300.6 s without a crossing cap track. Both examples remain **provisional candidates**.

Each event exposes `camera_boundary_evidence.possible_internal_edits` with the proposed time, temporal tier and crossing track IDs. The tier `isolated_spike` ranks a sharp frame change; `nonisolated_change` remains possible because some genuine broadcast dissolves are broad. `no_proposed_internal_edit` means only that this threshold found none, **not** that a stone was observed continuously. All 112 events state `physical_stone_identity_verified: false`.

Every `simulation_handoff` has `simulation_ready: false`, with exact release time, delivered-stone identity, continuous physical trajectory and settled board transition set to `null`. These fields should remain missing until video evidence or an independent reference verifies them. This export improves the data contract for later game-state reconstruction and coaching, but does not improve or validate throw precision/recall, establish a complete board sequence, or produce a physical simulation.
