# Counterless motion probe: China and Norway

The frozen 1 Hz [coloured-cap motion rule](../../prototype/stone_motion_fallback.py)
was applied without threshold changes. These are **source-video development
diagnostics**, not independent throw labels or F1 estimates.

## Canada–China 2022

The [nine counterless candidate scan](china-all-counterless-motion-probe-first.json)
uses each saved delivery window minus five seconds and plus 15 seconds. It
finds at least one supported moving-cap track in seven of nine windows. It
finds none for VISUAL-S403 and VISUAL-S593. S593 nevertheless has a
source-local yellow release cue and a same-colour receiving observation, so
"no track" cannot reject a candidate throw. The
[denser source-frame review](china-counterless-event-audit/README.md) shows
yellow travel near S52, red travel near S360, and yellow travel near S411.
The red S360 track conflicts with that candidate's provisional yellow colour;
it is a diagnostic conflict, not an automatic correction. The four
weak-window scan was separately frozen before the nine-window run; its
[first output](china-weak-event-motion-probe-first.json) agrees exactly with
the corresponding four rows of the all-nine run.

## Canada–Norway 2022 transfer

The identical rule was run across all 141 candidates in the saved
[Norway development ledger](../curlobserver-learned-probe/canada-norway-full-transfer/fused-linked.json).
The [frozen transfer](norway-full-event-motion-transfer-first.json) finds a
supported track in 83/99 counter-backed candidate windows (84%) and 30/42
counterless windows (71%). A hard motion-presence gate would remove 16
counter-backed candidates even though they have broadcast-counter support.
Counter support itself is a delayed broadcast proxy, so these are not 16
independently proven false negatives; the result still shows substantial
camera/method abstention on the stronger candidate group.

The [exact track-reuse audit](norway-motion-track-reuse-first.json) finds 155
track-to-window attributions but only 150 distinct exact track records. Five
tracks are attributed to two event candidates each, involving ten
candidates. Four pairs join a counterless and counter-backed proposal, and
one joins two counterless proposals. For example, the red track at
683–687 s supports both S43/B08 and counterless S45. Exact equality is a
lower bound on shared motion: overlapping search windows can cut the same
physical track into slightly different records. This establishes that
"motion seen near candidate" is not evidence for a *distinct* throw.

The [global exact-track registry](norway-motion-episode-registry-first.json)
deduplicates those 155 window attributions into 150 episode records and
preserves every candidate-to-episode link. Of 141 candidate windows, 107 have
at least one track linked exclusively to that window, six have only shared
tracks, and 28 have no supported track. These are linkage categories, **not**
107 verified throws: an exclusive exact record may still be part of the same
physical stone path as a nearby, slightly different record, and a window may
contain movement by an existing stone. The five shared episodes are left
unassigned; their motion is counted once rather than credited as separate
throw evidence for both linked candidates. The registry is reproducible with
`feasibility/scripts/python.sh
prototype/scripts/build_norway_motion_episode_registry.py` on a fresh output
path; the saved `first` output is guarded against overwrite.

An additional [near-duplicate audit](norway-motion-episode-near-duplicates-first.json)
flags three pairs of records with the same colour, essentially identical
endpoints and span, and overlapping times. Two pairs (S39/S40 and S63/S64)
are consistent with the same within-shot track being truncated by different
candidate search windows. The third (S376/S379) is a warning against merging
on pixel coincidence: sampled source frames change from an overhead view to
a front view between 5291 and 5297 s. The
[source-frame sheet](norway-motion-near-duplicate-source-frames.jpg) shows
that edit alongside the other two pairs. Those records cannot establish one
stone identity across the edit.

### Hard-cut-aware rerun

The baseline `verify_stone_motion_in_interval` did not pass cut times to its
tracker even though the tracker can break links at cuts. A separate
[cut-aware full transfer](norway-full-event-motion-cut-aware-v2.json) applies
the existing conservative [hard-cut test](../../prototype/scene_cuts.py) to
adjacent 1 Hz source frames and prevents a track from spanning a detected
edit. All 141 frozen search windows and colour rules are held fixed. The
[episode-link comparison](norway-cut-aware-episode-links-v2.json) records the
result. Supported candidate windows fall from **113 to 110**: S295, S376,
and S429 lose their only qualifying track, while the 99 counter-backed
windows remain 83 supported. The exact registry falls from 150 to **141**
tracks; five are still shared by multiple candidates. Two near-duplicate
pairs remain (S39/S40 and S63/S64); the S376/S379 cross-cut pair disappears.
Of 141 cut-aware candidate windows, 104 have an exclusive exact track, six
have shared tracks only, and 31 have no supported track. These counts do not
verify physical throw identity. The transfer is reproducible with
`feasibility/scripts/python.sh
prototype/scripts/probe_norway_full_event_motion_cut_aware.py`; the link audit
with `feasibility/scripts/python.sh
prototype/scripts/audit_norway_cut_aware_episode_links.py`. Both saved `v2`
outputs are guarded against overwrite. This is a development correction to
source-motion evidence, not a new event F1 score.

The [source-wide Norway catalog](NORWAY-GLOBAL-MOTION-CATALOG.md) then scans
each video second once within camera-shot boundaries before linking motion
to candidate windows. It exposes shared tracks and unlinked motion without
window-specific track duplication.

## Consequence for the detector

Keep moving-cap tracks as source evidence, not a binary throw filter. The
next detector stage needs a global, one-to-one assignment between candidate
events and motion episodes, respecting camera cuts and allowing abstention.
Its event precision/recall still requires an independent full-window source
reference on more than one production family. The existing official shot
counts and broadcast-counter links cannot replace that reference.
