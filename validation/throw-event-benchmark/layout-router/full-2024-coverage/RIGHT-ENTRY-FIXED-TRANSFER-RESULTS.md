# Fixed right-view entry rule: four-recording transfer

The post-Latvia right-view entry rule was replayed unchanged on **1650–2760 s** of the complete 360p Canada–Italy, Canada–Estonia, Canada–Scotland, and Canada–China 2024 recordings. This is an exposed development interval, not a reserved-match evaluation. The rule remains a **review proposal tier**, not an accepted throw detector.

| Recording | Raw right-colour tracks | Early-entry review proposals | Source-frame finding | Matching earlier coarse windows |
| --- | ---: | ---: | --- | ---: |
| Italy | 30 | 8 | 8/8 show moving stones in sampled first/line/confirmation frames | 8/8, same colour |
| Estonia | 23 | 8 | 8/8 show moving stones | 8/8, same colour |
| Scotland | 38 | 8 | 8/8 show moving stones | No frozen coarse reference |
| China | 50 | 10 | 10/10 show moving stones | 10/10, same colour |

The source-frame strips and hashed manifests are [Italy](right-entry-transfer/italy-source-review/manifest.json), [Estonia](right-entry-transfer/estonia-source-review/manifest.json), [Scotland](right-entry-transfer/scotland-source-review/manifest.json), and [China](right-entry-transfer/china-source-review/manifest.json). Each strip marks the tracked pixel at its first observation, nearest observed point to the interpolated y=250 line crossing, and the first qualifying confirmation. The source inspection was performed by the detector developer. Three stills demonstrate a short moving-stone image path; they do not establish full physical-throw identity, exact release or settle time, or completeness.

The earlier source-only, same-agent coarse delivery windows were frozen before this right-entry transfer. All 26 proposals in [Italy](../../canada-italy/blind-reference.json), [Estonia](../../canada-estonia-2024/blind-reference.json), and [China](../../canada-china-2024/blind-reference.json) fall within a matching-colour window, one-to-one. These checks are time/colour concordance, **not independent precision**. Conversely, only **8 of 17** Italy, **8 of 17** Estonia, and **10 of 18** China coarse windows have a right-entry counterpart. This review tier alone therefore leaves many earlier source-visible deliveries unmatched. Those fractions are not event recall: the coarse references are not certified exhaustive, and a right-view entry can be invisible or outside the fixed crop during a real throw.

The exact outputs are [Italy](right-entry-transfer/italy-1650-2760.json), [Estonia](right-entry-transfer/estonia-1650-2760.json), [Scotland](right-entry-transfer/scotland-1650-2760.json), and [China](right-entry-transfer/china-1650-2760.json). Each contains the source hash, all raw tracks including unpromoted ones, retained prefixes, crossing brackets, and code hashes. The fixed replay is [`transfer_right_entry_fixed_interval.py`](../../../../prototype/scripts/transfer_right_entry_fixed_interval.py); [`render_right_entry_transfer.py`](../../../../prototype/scripts/render_right_entry_transfer.py) verifies the source hash before rendering. Neither script changes the existing accepted event timelines.

The next detector decision needs a source-visible explanation for the unmatched windows: whether the right camera was absent, the entering stone lay outside the crop, the colour proposal failed, tracking broke, or the movement rule rejected a genuine path. That diagnosis can inform a camera-aware combination with the existing left-view proposals. It should be frozen before testing a separately labelled full recording; no high-F1 or full-match segmentation claim follows from this transfer.

## Diagnostic of the 26 unmatched coarse windows

Five source-only right-panel samples per unmatched coarse window are preserved with hashed manifests for [Italy](right-entry-transfer/italy-missed-windows/manifest.json), [Estonia](right-entry-transfer/estonia-missed-windows/manifest.json), and [China](right-entry-transfer/china-missed-windows/manifest.json). The receiving view is populated in at least part of every sampled window. Many strips show an entering stone; they also show occlusion, close-to-house motion, and at least one camera change (China C03). Sparse stills cannot establish what happened during every second or certify all coarse labels.

The machine-readable [Italy](right-entry-transfer/italy-unmatched-diagnostic.json), [Estonia](right-entry-transfer/estonia-unmatched-diagnostic.json), and [China](right-entry-transfer/china-unmatched-diagnostic.json) diagnostics compare the *starts* of same-colour raw tracks to each unmatched coarse window. **11/26** windows have no new same-colour raw track starting inside the window; **14/26** have new raw tracks, but every such track starts above the rule's y=250 entry line. The remaining window, Estonia E06, has raw red track R008 starting at y=314.5 and reaching y=221.5 within 12 seconds: it narrowly misses the rule's y<=220 confirmation requirement. These are raw colour-track diagnostics, not an attribution of each track to a delivered stone or a measured false-negative breakdown. Tracks that started before a coarse window can also span it.

Concrete source-linked examples: Italy I15 and I17 have visible moving yellow stones and raw starts at y=237 and y=239, so their available prefixes fail the y>=250 *first-observation* gate. Estonia E06 shows a red moving stone and the near-threshold R008 prefix. This points to entry-line geometry and incomplete early tracking as actionable hypotheses. Relaxing those gates without evaluating newly admitted player/equipment tracks would be premature; the accepted timelines remain unchanged.

## Postreview threshold probe

An isolated variant moves the image entry line and first-observation gate from **y=250 to y=235**, and the confirmation limit from **y<=220 to y<=225**. It retains the 60-pixel upward displacement, 20-second deadline, minimum initial cap area, and initial width/height rule. The [replay code](../../../../prototype/scripts/probe_right_entry_235_225.py) first verifies that the original y=250/y=220 rule reproduces each preserved candidate ID, then applies the variant to the *same* raw tracks. A separate [static-left replay](../../../../prototype/scripts/probe_right_entry_235_225_static.py) performs the same check on the previously inspected Latvia and Italy blind intervals.

| Source interval | Frozen review prefixes | Variant prefixes | Added raw track IDs | Lost frozen IDs |
| --- | ---: | ---: | --- | --- |
| Italy 1650–2760 | 8 | 10 | R025, R030 | 0 |
| Estonia 1650–2760 | 8 | 9 | R008 | 0 |
| Scotland 1650–2760 | 8 | 11 | R013, R016, R020 | 0 |
| China 1650–2760 | 10 | 10 | none | 0 |
| Latvia static-left 5015–6670 | 8 | 8 | none | 0 |
| Italy static-left 2835–3200 | 0 | 0 | none | 0 |

All six newly admitted short prefixes visibly follow moving stones in their sampled [Italy](right-entry-transfer/italy-variant-235-225-new-review/manifest.json), [Estonia](right-entry-transfer/estonia-variant-235-225-new-review/manifest.json), and [Scotland](right-entry-transfer/scotland-variant-235-225-new-review/manifest.json) source strips. The three Italy/Estonia additions align with previously unmatched same-colour coarse windows I15, I17, and E06. The Scotland additions have no frozen coarse delivery reference. The replay artifacts are [Italy](right-entry-transfer/italy-variant-235-225.json), [Estonia](right-entry-transfer/estonia-variant-235-225.json), [Scotland](right-entry-transfer/scotland-variant-235-225.json), [China](right-entry-transfer/china-variant-235-225.json), [Latvia](latvia24-full-v1/right-entry-variant-235-225.json), and [Italy static-left](new-preflight-italy24/right-entry-variant-235-225.json).

This variant was selected **after** inspecting the failures on these recordings. The sampled positives support its review value here, but they do not establish its false-positive rate or recall on unseen video. It remains a separate development artifact; no accepted event timeline or event-accuracy claim changes.

## Later transfer to Canada–Czechia

The same frozen and variant rules were then run on **1650–2760 s** of the full 360p Canada–Czechia recording, which had not been used to choose the y=235/y=225 thresholds. The [raw transfer](right-entry-transfer/czech-1650-2760.json) has 55 raw colour tracks and 10 frozen-rule review prefixes. The [variant](right-entry-transfer/czech-variant-235-225.json) retains those 10 and adds one, R051. The [11 source strips](right-entry-transfer/czech-variant-235-225-source-review/manifest.json) show a moving stone at the marked first/line/confirmation samples for every prefix, including R051. This is same-agent source review on an exposed recording, not independent precision.

A [source-hashed conditional join](right-entry-transfer/czech-variant-235-225-left-state-links.json) connects each right entry to exactly one earlier same-colour accepted left event within 20 seconds. All 11 are distinct left IDs, with right-minus-left image-event lags of **6.583–11.916 s**. The join then attaches the existing partial-state record: nine have a partial stable camera-local post-event board; one lacks stable stone observations in its registered tail; one has no quiet tail. The [join code](../../../../prototype/scripts/reconcile_right_entry_partial_state.py) abstains when zero or multiple prior left events satisfy the time/colour rule. These links offer a cross-camera review path into the game-state sequence, but timing and colour alone do **not** verify physical stone identity. No linked state is simulation-ready.
