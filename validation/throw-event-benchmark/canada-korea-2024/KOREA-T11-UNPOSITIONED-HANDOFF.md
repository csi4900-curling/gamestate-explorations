# Canada–Korea T11: template-to-cap handoff without a T11 position input

The [full-clip side-view cap scan](t11-sideview-cap-fullclip-development.json)
ran the previously frozen China-trained cap-context verifier at 1 Hz on the
entire 90-second Canada–Korea clip. It used yellow colour proposals in a
right-ice search area, a zero model-score threshold, and 30 px centre
suppression. The result contains **1,130 raw positive proposals** and
**198 suppressed candidate points**. Many are settled stones or other
objects; these are not 198 throw proposals.

The [handoff runner](t11-template-to-cap-handoff-development.json) reads the
full-clip cap scan and the earlier 0.45-score, yellow-handle-supported body
template paths. It does **not** read T11's provisional trajectory, reviewed
position samples, or the selected-frame cap-patch audit. The complete
90-second body scan has one upward seed, observed at **2308–2314 s**. From
its last position, nearest eligible positive cap points under a 130 px/s
image-motion gate extend the path at every second from **2315 through
2320 s**. Three consecutive steps of at most 4 px give a **visual-stillness
bracket of 2317–2318 s**, confirmed through 2320 s. The runner stops at that
confirmation rather than following a long stationary tail.

The [source-review sheet](t11-template-to-cap-source-review.jpg) and
[manifest](t11-template-to-cap-source-review.json) show the chosen boxes
on the same apparent yellow stone as it approaches the house and then on a
still-looking yellow stone. This is same-agent visual inspection, not
independent physical identity truth. In particular, a nearest-neighbour
handoff can switch stones near collisions or occlusions; still image position
does not establish an exact physical stop.

This is a concrete observation-layer gain over either appearance cue alone:
the template supplies a moving start; the cap verifier supplies later
observations after the body-template score drops. The body score and cap ROI
were selected after inspecting this clip, and there is no untouched
cross-match score for this fusion. The output therefore remains a
**development image path**, with physical throw, same-stone identity,
ground-plane trajectory, settled board, spin, and simulation readiness all
unverified. The next validation must freeze the combined rule and score it
against independently labelled full-video throws and receiving tracks in a
separate match.

A fixed-rule [Canada–Slovakia development transfer](../canada-slovakia-2024/YELLOW-HANDOFF-TRANSFER-RESULTS.md)
subsequently found a moving yellow body path but **no cap-verifier positives**
in its 80-second test window. The Korea handoff therefore does not yet transfer
as a complete observation path to that broadcast.

A **postreview** [raw yellow-contour continuation](yellow-contour-continuation-development.json)
does recover the same Korea visual-stillness bracket without the cap
classifier; its [source sheet](yellow-contour-continuation-source-review.jpg)
shows the linked points. The method was also fitted to the exposed Slovakia
clip before a [third-recording Estonia transfer](../canada-estonia-2024/YELLOW-CONTOUR-FIRST-TRANSFER-RESULTS.md)
revealed that the upward-only seed gate fails for a stone moving toward the
camera. It is not yet a robust cross-view event detector.

Reproduce with:

```sh
feasibility/scripts/python.sh prototype/scripts/scan_korea_sideview_cap_full.py
feasibility/scripts/python.sh prototype/scripts/fuse_korea_t11_cap_handoff.py
feasibility/scripts/python.sh prototype/scripts/render_korea_t11_cap_handoff.py
```

The JSON artifacts pin source, model, code, input and output hashes.
