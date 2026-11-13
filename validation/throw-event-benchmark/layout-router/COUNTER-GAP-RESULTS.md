# Counter evidence inside unsupported Beijing route gaps

The [predeclared inventory](COUNTER-GAP-PLAN.md) applies the frozen
monotone-counter model to the existing 300-second full-match preflights.
It keeps route gaps unchanged and separates counter evidence wholly inside
one gap from evidence that crosses a route boundary.

| Broadcast | Declared route gaps | Interior counter candidates | Boundary-ambiguous transitions |
| --- | ---: | ---: | ---: |
| [Canada–China](china22-counter-gap-inventory.json) | 3 | 1 | 1 |
| [Slovakia–USA](slovakia22-counter-gap-inventory.json) | 5 | 3 | 2 |
| [Sweden–Switzerland](swiss22-counter-gap-inventory.json) | 3 | 1 | 0 |

Canada–China's interior yellow update at 3662 s has counter evidence
within 3661–3662 s in the 3600–3900 s gap. A separate visual
gap probe observes a yellow moving-stone candidate at 3668–3671 s, and
[source frames](china22-gap-audit/yellow-motion-3663-3674.jpg) previously
showed a delivery there. The red update at 3629 s has evidence beginning
at 3596 s, before the gap; it remains boundary-ambiguous.

The other interior counter updates are Slovakia red 1163 s, yellow 3973 s
and yellow 6064 s, and Switzerland red 3907 s. Two-second source-only
contact sheets at [Slovakia 1135–1190](counter-gap-review/slovakia-1135/sheet-01.jpg),
[3940–4005](counter-gap-review/slovakia-3940/sheet-01.jpg),
[6030–6090](counter-gap-review/slovakia-6030/sheet-01.jpg) and
[Switzerland 3880–3935](counter-gap-review/swiss-3880/sheet-01.jpg)
show stones travelling during these windows. They support prioritizing
these gaps for continuous review, but sampled frames do not independently
validate each counter event's colour, exact throw time or identity.

This inventory proves a routing limitation: the current partial timelines
omit some counter evidence within intervals they label unknown. It does not
make those intervals complete. No counter read during an unknown interval
does not establish the absence of a throw; counter updates can lag releases
and may be wrong. Interior candidates are kept separate from confirmed
`observed_events`, and the route gaps remain explicit. Full-recording
precision, recall and F1 are still unmeasured.
