# Frozen scoreboard-marker transfer: geometry failure

The unchanged [2024 active-end scanner](../../../../prototype/scripts/scan_2024_end_markers.py)
was run at 10-second steps over the full Canada–Latvia and Canada–Scotland
360p sources. Its [Latvia scan](../../canada-latvia-2024/end-marker-full-transfer.json)
calibrated no scoreboard panel and recognized **0/706** sampled markers.
The [Scotland scan](../../canada-scotland-2024/end-marker-full-transfer.json)
recognized **325/735**, but its end number is not reliable.

The pinned [source crops](marker-transfer-failure.jpg) show the failure
directly. At Scotland 930 s, the red chevron is visibly under column **2**,
while the scanner reports end **3** with 0.956 image similarity. At Latvia
2000 s, the scoreboard and yellow chevron are visible, but the scanner emits
`null`: this scoreboard sits lower in the image than the frozen colour-panel
calibration expects. The [crop manifest](marker-transfer-failure.json) fixes
both source and scan hashes. These are developer-inspected source examples,
not independent end labels.

The Scotland scan's apparent sequence and its 325 hits must therefore **not**
be joined to the throw candidates as physical or displayed end identities.
End-level official counts remain useful global constraints only. The next
marker reader needs a two-dimensional board registration and a check that the
predicted chevron column agrees with the visible printed column number.
Only after source checks across multiple end changes should its output be
used for per-end candidate accounting. Marker changes would still bound
broadcast graphic changes, not exact physical end transitions or deliveries.

A separately versioned [2D transfer](2D-MARKER-CANDIDATE-CONTEXT.md) now fits
both image axes and source-checks one positive marker per displayed end. It
attaches provisional broadcast-display run context to candidate ledgers; the
failed frozen scan remains preserved here for comparison.
