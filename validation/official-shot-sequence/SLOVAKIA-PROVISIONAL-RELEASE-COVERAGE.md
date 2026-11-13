# Within-view release-cue coverage of the provisional Slovakia ledger

The [source-scoped audit](slovakia-provisional-release-coverage-development.json) applies the existing unchanged held-to-motion cap cue to **all 116** provisional event windows in the Slovakia full-match union. Selection uses the union's source-shot windows, not official throw labels or counter colours. Each result retains the source hash, full evidence window, any passages, cue time, ledger colour relation, and explicit false flags for verified physical identity and simulation readiness.

| Outcome | Event windows |
| --- | ---: |
| Exactly one within-view passage | 34 |
| No passage | 80 |
| Multiple passages; abstain | 2 |
| Unique cue agrees with ledger colour | 30 |
| Unique cue conflicts with ledger colour | 1 |
| Unique cue; ledger colour unknown | 3 |

The unique-cue coverage is **34/116 (29.3%)** of *existing candidates*, not physical throw recall. Candidate windows are incomplete and may include wrong events. A cue time is a detected cap motion onset inside a broadcast view, not an exact release instant or a cross-view trajectory. The 30 colour agreements are internal consistency checks, not independent precision.

The one colour conflict is S146: the cue is red at 2447.4 s while the linked ledger colour is yellow. [Source frames](slovakia-s146-release-conflict.jpg) show red and yellow stones clustered near the house and a player/broom in the view. The red cap passage could arise from an existing stone or interaction near the house; it cannot be promoted as the delivered stone. Conversely S411, previously unlinked and colour-ambiguous, has a yellow within-view cue at 6386.8 s, agreeing with separate held-cap and post-cut yellow evidence. That combination strengthens the review hypothesis but still lacks verified cross-cut physical identity.

No provisional event count or counter link changes. This sidecar can help prioritize review and narrow selected within-view time windows, while the full detector still needs independent complete-recording labels, reliable identity across camera cuts, and settle-state validation. Reproduce with `PYTHONPATH=prototype feasibility/scripts/python.sh -u prototype/scripts/audit_slovakia_provisional_release_coverage.py` from the project root.
