# Latvia displayed end 6: periodic receiving-house observations

The [dense lower-ice probe](LATVIA-END6-DENSE-RIGHT-PROBE.md) found that the
surviving upward colour paths during the static-left overlap were player
pixels. A separate [periodic right-house scan](latvia24-full-v1/end6-periodic-right-board-development.json)
asks whether image-stable coloured caps change while no right-entry proposal
survives. It reuses the existing three-frame, same-colour, ≤5 px observer
every ten seconds from **5670 to 6670 s**, sampling each window at +0, +2 and
+4 seconds. These are image observations, not a complete board.

Of **100** windows, 48 have at least one repeated colour-cap proposal, 22
have none, and 30 abstain on large scene/player change. Among 99 successive
window pairs, 27 have two usable cap sets and pass the existing painted-house
image-alignment check; two further usable pairs fail that alignment check,
and 70 lack a usable set on one side. **Fifteen of the 27** conditional pixel
comparisons have one or more unmatched blobs. Those differences form review
windows only: an unmatched blob cannot establish a delivered, moved or removed
stone. All rows retain false physical-board and simulation-readiness flags.

The [marked source examples](latvia24-full-v1/end6-periodic-board-source-review.jpg)
at 5902–5922, 6332–6342 and 6552–6572 s show why. Some circles land on
visible stones; others overlap people or wheelchair details, and foreground
motion changes what is visible. The [source-review manifest](latvia24-full-v1/end6-periodic-board-source-review.json)
and [scan runner](../../../../prototype/scripts/scan_latvia_end6_periodic_boards.py)
pin the inputs and method. The examples were selected after seeing proposals,
so they are development failure analysis, not independent validation.

All **15** unmatched adjacent comparisons have now been rendered in three
[source sheets](latvia24-full-v1/end6-all-cap-changes-01.jpg)
([second](latvia24-full-v1/end6-all-cap-changes-02.jpg),
[third](latvia24-full-v1/end6-all-cap-changes-03.jpg)). Magenta marks the
unmatched pixels. The [manifest](latvia24-full-v1/end6-all-cap-changes-manifest.json)
records the inspected pair times and the same-agent conclusion: none of the
sampled before/after frames verifies a delivered-stone arrival or physical
board transition. A throw could still occur between sampled frames; this
review does not label the entire intervals as throw-free.

A [selected 1080p source check](LATVIA-END6-HIGHRES-RESOLUTION.md) confirms
that larger stone bodies and handles are visible, while player and wheelchair
occlusion persists in the three inspected failure frames. It does not change
the event or physical-board conclusions above.

This sequence contributes conditional, time-indexed *partial image state* in
the detector's blind interval, but cannot reconstruct the physical board or
recover event times. A stone-body detector with occlusion handling and
camera-pose checks is needed before differences can become state transitions.
Full-interval independent throw and board labels remain necessary to score
recall and game-state accuracy.
