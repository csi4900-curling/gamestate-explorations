# Beijing counter monotonicity development audit

The initial full Canada–China 2022 routed [timeline](full-china22-partial/timeline.json)
contains 119 provisional events in supported runs. A prior reset-blink fix
removed the 2825 s red and 7327 s yellow duplicate decrements on a fresh
[full run](full-china22-current-model/timeline.json), leaving 117.

A chronology audit of that fresh run still found adjacent red events at 4230
and 4263 s. The underlying counter states were `[6,5]` → `[7,5]` → `[6,5]`
→ `[5,5]`. One row rose and returned before the next monotone decrement.
The [source-only 4215–4275 s sheet](full-china22-current-model/sequence-review-4215/sheet-01.jpg)
shows active play, but cannot independently establish exact throw identity
or colour. The upward count read is concrete evidence that accepting its
return as a new decrement is unsafe.

`ScoreboardEvents` now retains the last monotone state when a stable one-row
rise occurs, records the rise as unresolved once, and waits for a subsequent
decrement from that state. It still accepts a corroborated two-row end reset.
The change was tested with a rise–return–real-decrement sequence and replayed
through saved whole-source counter observations. On the 8,356 s replay,
relative to the prior reset-blink model, it removes provisional red events
at 4230 and 6967 s and recovers yellow 788 s and red 912 s. The
[source sheets near 775 s](full-china22-current-model/monotone-review-775/sheet-01.jpg),
[900 s](full-china22-current-model/monotone-review-900/sheet-01.jpg) and
[6950 s](full-china22-current-model/monotone-review-6950/sheet-01.jpg)
offer context but are too sparse to certify the revised event identities.

The complete adapter was rerun from video with the revised model. Its
[new timeline](full-china22-monotone-model/timeline.json) has 117 provisional
events over the **same three coverage gaps**. Relative to the original
119-event timeline, it removes 2825, 4230, 6967 and 7327 s and adds 788 and
912 s. The model's [sequence audit](full-china22-monotone-model/sequence-audit.json)
has six same-colour adjacent pairs and none within 40 seconds in one
supported run, down from twelve and three in the original timeline.
That is a consistency improvement, not an event-F1 measurement. The
pipeline's `--resume` verification reproduced the new output exactly.

On the three previously measured 1650–2760 s Beijing recordings, the new
adapter produced exactly the prior event colour/time/evidence-kind lists:
[Canada–China](../paralympics-2022-canada-china/development-v9-monotone.json)
20, [Sweden–Switzerland](../paralympics-2022-sweden-switzerland/development-v9-monotone.json)
19 and [Slovakia–USA](../paralympics-2022-slovakia-usa/development-v9-monotone.json)
16. These are exposed development intervals, so equal predictions establish
regression stability there, not new generalization. The full recording still
has unknown gaps and no exhaustive independent throw reference. High
precision, recall and F1 remain unproven.

The [two-other-match transfer](MONOTONE-TRANSFER-RESULTS.md) replays the
frozen change over Slovakia–USA and Sweden–Switzerland full counter streams.
It finds further event-key changes, including removal of repeated
rise-and-return decrements. Sparse source sheets offer context but do not
turn those counter keys into an independent throw reference.
