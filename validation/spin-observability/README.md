# Stone rotation: T11 source-video feasibility check

The 2D stone trajectory does **not** identify a revolution count. Different rotation rates, ice conditions, sweeping, and collisions can produce similar paths. The existing game-state handoff therefore leaves `turn_revolution_count` unknown.

There is a more promising measurement in the **video pixels**. On the 1920 × 1080 Canada–Korea source recording, the yellow stone's asymmetric handle is visibly resolved in sampled frames of throw T11. The [departure and arrival sheet](T11-departure-arrival-contact.png) shows samples from source times 2303.5–2319.0 s. The [receiving-camera handoff sheet](T11-receiving-handoff-contact.png) shows samples from 2306.7–2312.0 s, including the far range omitted by the initial bounded receiving-camera trajectory. These are original-resolution frame crops resized for inspection, **not** inferred handle angles.

This supports a **feasibility hypothesis** for video-based spin tracking on this recording, not a measured number of turns. A measurement would have to isolate the yellow handle, estimate its angle relative to each camera, unwrap angle through consecutive source frames, and reconcile the two cameras' viewpoints at the handoff. Side-view silhouette, motion blur, occlusion, and low apparent size can make an angle ambiguous. Sparse trajectory samples at 0.5 s intervals cannot resolve a fast rotation, even where the handle appears clear in a still frame. Any interval without an unambiguous orientation sequence must remain unknown or have an explicitly bounded count; interpolation is not ground truth.

The existing `results.json` records the initial bounded trajectory gap from 2306.7 to 2312.5 s, but the expanded receiving-camera probe observes a stone during that interval. The first gap is a processing limit, not proof of visual absence. The identity and metric handoff between cameras remain provisional. This check makes no revolution-count claim.

Source: `prototype/throw-analysis/end3.mp4`, source offset 1650 s, SHA-256 in `prototype/throw-analysis/source.json`; sample centers from `prototype/cross-view/results.json` (`T11.departure`, `T11.arrival`, `T11.display_arrival`).

## Consecutive-frame pilot

The [moving quarter-second sheet](T11-moving-quarter-second.png) shows the
handle changing continuously from 2307.0 to 2312.75 s. The
[settled control sheet](T11-settled-quarter-second.png) shows a nearly fixed
handle from 2319.5 to 2323.0 s. The [one-second side-view strip](T11-handle-side-silhouettes.png)
shows why a count is harder than spotting motion: the silhouette at 2307 s
faces the opposite way from 2309 s and returns to a similar orientation near
2311 s.

The reproducible [mask-repeat probe](T11-handle-periodicity-first.json) samples
56 moving and 36 settled frames at 10 Hz. Its strongest moving-mask similarity
between 0.8 and 3.0 s occurs at a **2.1 s image lag** (mean intersection over
union 0.671 across 35 frame pairs). Similarity drops to 0.491 at a 1.0 s lag.
This is evidence of a repeated image pattern, **not** a measured revolution
period. Opposite side-facing handle positions can share substantial mask
overlap, so a 2.1 s silhouette repeat may alias a half turn. The settled
control also varies because the camera image blurs and objects pass nearby.
The first defensible revolution count requires a calibrated angular phase
tracker that distinguishes the mirrored handle poses, unwraps them through
the camera handoff, and marks intervals without reliable pixels as unknown.

Run `feasibility/scripts/python.sh prototype/scripts/probe_t11_handle_periodicity.py`
after moving its frozen JSON output aside. The artifact records the source,
track and code hashes. It supplies no full-throw spin count or simulation
parameter yet.

## Signed side-view silhouette pilot

The [polarity plot](T11-handle-polarity-pilot.png) and reproducible
[measurements](T11-handle-polarity-pilot.json) compare each 10 Hz moving frame
with two handle silhouettes selected from the beginning of the clip. Positive
values resemble the early left-facing image; negative values resemble the
later right-facing image. The mean signal is **+0.0699** at 2307.0–2307.4 s,
**−0.0649** at 2308.5–2309.3 s, and **+0.0275** at 2311.0–2311.5 s. A
separate settled control stays negative over 2319.5–2323.0 s (mean −0.0422).
This establishes a measured **left/right/left visual sequence** in one
receiving-camera interval. It also explains why a 2.1 s unsigned mask repeat
could alias opposite handle poses.

The selected templates and intervals came from inspection of this exposed
clip. The polarity is a two-pose image descriptor, not a calibrated angular
phase or a count of physical revolutions. Camera viewpoint and yellow-mask
quality can change the signal, especially near 2312 s. We still leave the
full-throw `turn_revolution_count` unknown until an angle tracker can unwrap
rotation through the camera handoff and mark obscured intervals explicitly.

## Same-recording transfer check

The unchanged T11 templates were applied to the first five seconds of the
receiving-camera track for **all seven other yellow throws** in the end-three
ledger. The [transfer sidecar](T11-template-yellow-transfer.json) records 26
samples per throw at 5 Hz, the T11 polarity, and whether the yellow component
reaches the crop edge. Masks were available throughout, but T13 had four
edge-clipped samples; its trajectory center visibly places the handle close
to the crop boundary. The signed scores vary in every throw, but their
positive/negative patterns do not by themselves supply pose labels or a
calibrated phase. A T11-only silhouette template is therefore **not promoted
as a general spin counter**. The next version needs stone-centered handle
localization and an orientation descriptor that is robust to scale, camera
pose, occlusion, and other yellow objects.

A conservative [local-centering audit](T11-localized-handle-transfer.json)
then searched a wider patch around each provisional trajectory point. It
recentered only when exactly one plausible yellow component was present; it
abstained when several were nearby. Across the 182 transfer frames, this
produced 160 unclipped polarity observations and **22 explicit ambiguous
frames**. T13's original four edge-clipped frames became two abstentions and
two recentered observations, with no remaining edge-clipped accepted crop.
The recentering improves crop observability, but does not establish that the
chosen component is the delivered stone or calibrate left/right pose across
throws. Physical revolution counts remain unknown.

## Centroid control

The reproducible [handle-centroid audit](T11-handle-centroid-control.json)
tests a simpler angle cue: the horizontal centroid of the same normalized
yellow handle mask used by the polarity pilot. It samples 56 moving and 36
settled-control frames at 10 Hz. The moving centroid spans 6.938 normalized
pixels, but the settled control still spans 3.227 pixels; maximum adjacent
changes are 4.731 and 1.622 pixels respectively. Apparent motion of this
descriptor therefore includes segmentation, scale-normalization and image
variation even when the stone is stationary. These samples do not calibrate
centroid offset to a physical angle or distinguish a half-turn from a full
turn. The signed silhouette sequence remains useful visual evidence, while
the revolution count stays unknown.

Reproduce with
`feasibility/scripts/python.sh prototype/scripts/audit_t11_handle_centroid.py`
after moving its frozen JSON output aside. The artifact pins the source video,
track, mask extractor and audit code by SHA-256.
