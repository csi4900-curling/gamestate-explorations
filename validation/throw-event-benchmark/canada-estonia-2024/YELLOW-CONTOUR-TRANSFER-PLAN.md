# Frozen yellow body-to-contour transfer window

The next development transfer of the Korea/Slovakia yellow-contour
continuation is Canada–Estonia 2024 source seconds **1720–1800**, local
seconds 70–150 of `source-1080p-1650-2760.mp4`. The clip SHA-256 is
`eaa88f73b56ea982808468a642ad5481428e758881f41cfaf812be58f949a533`.
This window was chosen before running the new right-view contour rule because
the already exposed left-view candidate S02 is yellow with crossing time
1759.52 s. S02 is a provisional left candidate, not independent throw truth.

Run the unchanged Latvia yellow body template at 0.45, matching-colour handle
gate, original body ROI, and existing one-second upward path linker. For each
upward body seed, use the fixed raw yellow HSV contour mask, minimum area 15
at 640×360, original right-ice ROI, +18 px image body proxy, 130 px/s motion
gate, one-second predicted-centre association cost, and three one-second
steps of at most 4 px to mark visual stillness. Do not use S02 coordinates or
any target source review in detector execution.

Retain all body proposals, upward paths, contours and handoffs. Render every
upward predicted path for same-agent source review. Report failures and
ambiguities. This is a nonblind development transfer, not full-video
precision, recall, F1, physical stone identity, or game-state validation.
