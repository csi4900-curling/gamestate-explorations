# Isolated split-view gap bridge, postscore development

The first [Scotland full-source result](LATVIA-SCOTLAND-RESULTS.md) left six
90-second interior chunks unknown despite source stills showing split-screen
match play. A separate [bridge rule](../../../../prototype/layout_gap_bridge.py)
now marks an unknown 90-second chunk as conditional split-view coverage only
when it has split-screen chunks on **both** sides, at least four of nine
split-signature samples, and at most one Beijing-only counter sample. The
frozen original preflights and timelines are unchanged. The rule was designed
after inspecting Scotland and is therefore a development fit.

The [saved preflight replays](short-gap-bridge/) show what the fixed rule does
on seven full-source controls:

| Source | Newly bridged chunks | Remaining unknown |
| --- | ---: | ---: |
| Scotland 2024 | Six interior chunks, 540 s | 0–90 and 7200–7347 s |
| Latvia 2024 | 0 | 219 s |
| Italy 2024 | One late 90 s chunk | 150 s |
| Estonia 2024 | One late 90 s chunk | 153 s |
| China 2024 | 0 | 347 s |
| USA 2024 | 0 | 353 s |
| China 2022 Beijing | 0 | Original gaps unchanged |

The unchanged 2024 [adapter replay](scotland24-bridged-development/timeline.json)
over Scotland's now continuous 90–7200 s supported run emits 194 raw motion
proposals and 122 context-accepted candidates. All 112 candidates from the
[original partial timeline](scotland24-full-v1/timeline.json) recur at the
**same timestamp and colour**. The ten additional candidates lie in five
previously unknown chunks: three at 2070–2160, one at 2250–2340, one at
4500–4590, two at 6120–6210 and three at 7020–7110 s. The 3870–3960 s
chunk yields no accepted candidate. The [additive triage](scotland24-bridged-development/bridge-review-triage.json)
keeps the original 112-count timeline intact and places all ten additions in
`new_from_bridged_layout_needs_physical_stone_verification`. Six new claims are
red and four yellow; blindly accepting all ten would produce 67 red and 55
yellow candidates, still incompatible with the normal 56/56 completed-end
colour capacity.

The [event-time layout audit](scotland24-bridged-development/event-layout-audit.json)
decodes source frames at each candidate crossing and ±1 s. Three of the ten
new candidates have zero split-signature matches, but this image signature
cannot be a hard veto: the [source sheets](scotland24-bridged-development/new-event-source-review/manifest.json)
show a visible yellow stone in transit around the 2298.41 s candidate despite
its zero signature score. The sheets also show no corresponding red stone in
motion around the 6147.40 s red claim; a player occupies the tracked crossing
during end changeover. The 2102.30 s red claim tracks a Canadian jersey logo
while a yellow stone is visible. A later
[crossing-pixel and frozen-patch audit](CROSSING-PATCH-FAILURES.md) shows that
the patch model still accepts three clear non-stone crossings among the ten
new candidates. These are prediction-targeted inspections, not exhaustive
throw labels or a false-positive-rate estimate. Other recovered windows visibly
contain travelling stones, but delivered-stone identity remains unverified.

The late [Italy bridge control](short-gap-bridge/italy24-promoted-run/events.json)
emits one raw proposal and no accepted event. The late
[Estonia control](short-gap-bridge/estonia24-promoted-run/events.json) emits
nine raw proposals and **one accepted red event at 3870.62 s**. Its
[source frames](short-gap-bridge/estonia24-promoted-run/source-review/sheet-01.jpg)
show a red broom head moving amid end cleanup and no visible red delivery at
that instant. This is a concrete reason to keep bridged candidates out of the
accepted throw sequence until a physical-stone/phase verifier is validated.

The rule improves **proposal coverage**, not measured throw recall or F1. The
next implementation gate is to distinguish delivered stones from brooms,
clothing and changeover motion without rejecting real stones whose scoreboard
or split signature is weak. An independent source-first complete-match event
reference is still required before claiming high precision and recall.

Reproduce the saved routes with
[`replay_layout_gap_bridge.py`](../../../../prototype/scripts/replay_layout_gap_bridge.py),
the Scotland pass with
[`run_bridged_2024_timeline.py`](../../../../prototype/scripts/run_bridged_2024_timeline.py),
and the additive review ledger with
[`build_bridged_event_triage.py`](../../../../prototype/scripts/build_bridged_event_triage.py).
