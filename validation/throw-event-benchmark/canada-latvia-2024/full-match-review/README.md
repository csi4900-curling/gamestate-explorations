# Latvia full-match evidence explorer

Open [index.html](index.html) directly in a browser. It uses the pinned
`../source-360p.mp4` and adjacent generated `data.js`, so no web server is
needed. The timeline marks the original routed gaps and the 5015–6670 s
static-left interval. Select any of the **127 ordered evidence rows** to seek
its source time. Filters separate 72 provisional left passages, 47 left-screen
abstentions, and eight right-only review entries. The right entries show their
observed image-prefix points and, where available, repeated camera-local cap
proposals and guarded adjacent-cap status.

The displayed path is an image-coordinate summary across its observed prefix,
not an instantaneous full trajectory. A cap is an image observation, not a
verified physical stone. The page leaves exact release, settling, persistent
stone identity, complete board, spin and simulation readiness unknown. It
exposes model predictions and therefore **must not** be used for independent
throw labeling. Use a prediction-blind packet for that purpose.

The "Source-reviewed person pixels" filter exposes three previously inspected
crossings. One, S45, is still among the 72 provisional left passages because
the original screen accepted it; the viewer flags its visible player pixels
and links the marked source crop. Four other reviewed crossings show a stone
body at the tracked pixel, but none verifies a physical throw. The remaining
rows have no such source-pixel classification.

The viewer is generated from the [full-match handoff](../../layout-router/full-2024-coverage/latvia24-full-v1/full-match-candidate-partial-state-handoff.json)
by [`build_latvia_full_match_viewer.py`](../../../../prototype/scripts/build_latvia_full_match_viewer.py).
[provenance.json](provenance.json) records hashes for the handoff, source video,
generated data and UI. The [browser capture](browser-r005.png) shows one
right-only entry and four partial cap proposals. The repeatable
[browser check](../../../../prototype/scripts/check_latvia_full_match_viewer.py)
verifies all four evidence filters, the right prefix overlay, four R005 cap proposals,
disabled cap navigation on raw abstentions, the reviewed-person filter, and
the absence of page errors;
[browser-check.json](browser-check.json) records the outcome.
