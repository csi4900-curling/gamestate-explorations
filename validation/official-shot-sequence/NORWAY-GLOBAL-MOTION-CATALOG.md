# Norway source-wide motion catalog and candidate links

The [source-wide catalog](norway-global-shot-scoped-cap-motion-first.json)
samples the entire 9,039-second Canada–Norway source once at 1 Hz, applies the
same narrow red/yellow cap rule used in the earlier local probe, and links
tracks only within the 709 camera shots of the saved
[shot manifest](../curlobserver-learned-probe/canada-norway-full-transfer/shot-review/manifest.json).
It finds **169 source motion tracks**. Each track has one catalog ID and one
camera-shot ID before candidate-event windows are considered. It is still a
*cap-motion catalog*, not a catalog of physical throws: old stones, replays,
other objects and coverage gaps remain possible.

The [candidate link graph](norway-global-cap-motion-candidate-links-first.json)
joins these tracks to the frozen 141 Norway event candidates by compatible
colour and overlap with each candidate's declared search interval. It has
**142 possible links**. Eight catalog tracks are linked to two candidates
each; 35 catalog tracks link to no candidate. Among candidates, 99 have at
least one exclusive catalog track, ten have only shared tracks, and 32 have
none. An exclusive link means only one *candidate window* intersects that
track; it does **not** verify that the track is the delivered stone.

The graph shows why scanning separately in overlapping event windows is
unstable. The S39/S40 pair now links to the single global track `S40-R01`,
and S63/S64 both link to `S64-R01`; their earlier local results contained
near-identical truncated records. Eight shared tracks remain explicit rather
than being counted as separate observations. Only **30 candidates** have a
compatible track within their own origin camera shot and delivery interval;
20 of those carry delayed broadcast-counter support. The remaining temporal
links are in other shots or the expanded search period and need stronger
identity evidence before an event can be confirmed.

The [coverage comparison](norway-global-cap-motion-coverage-first.json)
shows 110 candidate windows with a track in the cut-aware local scan versus
109 linked to the global catalog. Three local-only candidates (S53, S243,
S465) and two global-only candidates (S217, S514) show that clipping a track
to a candidate window, and the different cut boundaries, can both create and
remove qualifying motion evidence.
These differences cannot be read as true/false throw decisions. The 35
unlinked catalog tracks are a useful recall-review queue, but some may be
replays, existing stones, or non-stone colour detections.

The first [adjacent-origin review audit](NORWAY-UNLINKED-MOTION-RESCUES.md)
finds five source-backed proposals in that queue: three origin shots missing
from the candidate ledger and two provisional colour conflicts. None is
silently inserted into the main timeline.

Reproduce the catalog and graph with:

```sh
feasibility/scripts/python.sh prototype/scripts/build_norway_global_cap_motion_catalog.py
feasibility/scripts/python.sh prototype/scripts/link_norway_candidates_to_global_cap_motion.py
feasibility/scripts/python.sh prototype/scripts/audit_norway_global_cap_motion_coverage.py
```

The three outputs preserve source/code hashes and refuse to overwrite the
first runs. The next detector step is a constrained candidate-to-episode
assignment that can abstain, informed by release cues, camera-shot context,
and board transitions. Independent physical-event labels across recording
families are still required for precision, recall, and F1.
