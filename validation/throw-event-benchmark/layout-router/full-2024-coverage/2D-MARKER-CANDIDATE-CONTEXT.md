# Registered scoreboard displays and full-match candidate context

The [first frozen marker transfer](MARKER-TRANSFER-FAILURE.md) failed because
it assumed one scoreboard row and misregistered a Scotland column. A separate
[2D panel-registered scanner](../../../../prototype/scripts/scan_2024_end_markers_2d.py)
fits the red/yellow board position in both image axes, then applies the
unchanged chevron template. It ran at 10-second steps on both complete 360p
recordings. Its output is **display evidence**, not a physical end or throw
label.

| Match | Source frames with a recognized marker | Repeated displayed-end runs | Accepted passage candidates inside repeated runs | Outside those runs |
| --- | ---: | --- | ---: | ---: |
| [Latvia](../../canada-latvia-2024/end-marker-full-2d-local-development.json) | 290 / 706 | 1–6 | 70 / 72 | 2 |
| [Scotland](../../canada-scotland-2024/end-marker-full-2d-local-development.json) | 127 / 735 | 1–7 | 91 / 112 | 21 |

One positive source crop for each displayed end was inspected in the
[Latvia](latvia-2d-marker-source-review.jpg) and
[Scotland](scotland-2d-marker-source-review.jpg) sheets. Their printed
columns agree with the reader in those **13 selected cases**; the
[manifest](2d-marker-source-review.json) records source, scan, image and
script hashes. This is a prediction-exposed spot check, not full-scan or
independent accuracy. Occluded and unreadable markers remain unassigned.

The existing two-hit temporal rule produces six Latvia runs from 200–6860 s
and seven Scotland runs from 360–7270 s, each with gaps between observed
graphic runs. The [candidate joiner](../../../../prototype/scripts/attach_2d_display_runs_to_full_match.py)
uses only intervals bounded by the first and last repeated hit for that
displayed end. It does not extend a run into an unobserved gap. The
[Latvia candidate ledger](latvia24-full-v1/candidate-display-run-context-development.json)
and [Scotland candidate ledger](scotland24-full-v1/candidate-display-run-context-development.json)
retain all 72 and 112 accepted proposals, respectively, with source/input/code
hashes. Every row keeps `physical_end_identity: null`,
`physical_throw_verified: false` and `simulation_ready: false`.

The Latvia ledger has 14, 16, 16, 16, 7 and 1 accepted proposals inside
displayed runs 1–6. The sharply lower counts in runs 5–6 are a **review
priority**, consistent with the known static-left camera failure, but they
are not missed-throw counts: the graphic can lag play, accepted proposals
include false paths, and the detector can miss or duplicate throws. Scotland's
21 candidates outside repeated marker runs likewise remain candidates with
unknown display context, not newly identified end-boundary throws. Neither
ledger is used to promote per-end F1 or complete game state.

The display context is also joined to the broader, conserved partial-state
handoffs as **sidecars**: [Latvia's 127 rows](latvia24-full-v1/full-candidate-display-context-development.json)
include 72 accepted left passages, 47 withheld left motions and eight right-only
review entries; [Scotland's 125 rows](scotland24-bridged-development/full-candidate-display-context-development.json)
retain its bridged sequence. The sidecars preserve the original handoffs by
hash and do not edit their board observations or readiness flags. Latvia has
all eight right-only entries inside displayed run 5, while run 6 contains one
accepted left passage, three withheld left motions and **no** right-only entry.
The known static-left interval overlaps the first 1000 s of displayed run 6
(5670–6670 s). This makes that interval a specific source-review and detector
coverage target, not a claim that the interval has no deliveries. Scotland has
22/125 candidates outside repeated marker-hit intervals, including one
right-entry proposal; they remain unassigned rather than forced into an end.

The resulting [dense Latvia run-6 right-view audit](LATVIA-END6-DENSE-RIGHT-PROBE.md)
samples the entire 5670–6670 s blind overlap every 0.5 s. Four upward red
colour paths survive a loose image-motion linker, but marked source frames
place all four on players' clothing. This narrows the recovery problem to
stone/body identity and visibility rather than a missing set of colour-motion
samples.
