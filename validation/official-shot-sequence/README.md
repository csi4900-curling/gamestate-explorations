# Official 2024 game-results count audit

For the 2022 Beijing recordings, see the separate
[independent official shot-order reference](PWG2022-SHOT-REFERENCE.md). Its
results book includes numbered shot-by-shot pages for three videos already
in the project; the 2024 wheelchair book discussed below does not.
Its [post-shot board-state reference](PWG2022-BOARD-STATE.md) extracts the
embedded diagrams for all 349 numbered shots.

The [2024 World Wheelchair Curling Championship results book](https://curlit.com/PDF/WWhCC2024_ResultsBook.pdf?V=2)
contains the Canada–China, Canada–Estonia and Canada–Italy game-results pages
(PDF pages 75, 69 and 86). The published YouTube titles identify the three
development recordings as those team pairings at WWhCC 2024. The downloaded
PDF and timeline hashes are recorded in
[2024-game-results-audit.json](2024-game-results-audit.json); rerun the
[extraction script](../../prototype/scripts/audit_official_game_results.py)
to reproduce the structured scores and count comparison.

The book **does not contain shot-by-shot pages for these matches**, despite
such pages existing for other curling events. It offers end scores and an `X`
for an unplayed or unfinished end. Under the [World Curling description of
team curling](https://worldcurling.org/about/curling/), each completed end
normally contains eight deliveries by each team. This is a nominal count
constraint, not an event-timed reference or a license to discard candidates.

| Video | Official completed ends | Nominal deliveries in those ends | Provisional timeline events | Difference |
| --- | ---: | ---: | ---: | ---: |
| Canada–China | 8 | 128 | 131 | +3 |
| Canada–Estonia | 7; end 8 `X` | 112 | 128 | +16 |
| Canada–Italy | 7; end 8 `X` | 112 | 109 | −3 |

China's provisional count exceeds the normal eight-end delivery count by three. Estonia's
and Italy's differences cannot be interpreted until the `X` end's actual
delivery count and the broadcast's play boundaries are established. Any
count discrepancy could involve extras, misses, redeliveries, or video outside
match play. The provisional timelines also have explicit coverage gaps. The
PDF supplies no event timestamps or physical-stone identities, so it cannot
produce precision, recall or F1 by itself.

The colour count provides a second coarse constraint. Across at most eight
ends, one handle colour normally contributes no more than 64 deliveries.
China has 68 provisional red and 63 yellow events; Estonia has 65 red and 63
yellow. Their red counts exceed that normal capacity by four and one,
respectively. A wrong colour, duplicate, equipment event, redelivery or
outside-play detection could explain the excess. The count alone cannot say
which event is wrong.

The [source-reviewed China end count](china-end-count-audit.json), reproduced by
[audit_china_end_sequence.py](../../prototype/scripts/audit_china_end_sequence.py),
removes four visibly non-stone red tracks. The remaining 127 provisional
events divide into seven ends with 16 candidates each and a final end with
15 (eight red, seven yellow). The [final-play frames](china-final-play-sequence.jpg)
show the last red stone entering the house around 7912–7920 s, followed by
players gathering and the broadcast closing without another visible
delivery. Thus the apparent missing yellow is consistent with the recorded
match ending after 15 deliveries; 128 is not an appropriate fixed target for
this game. These reviews are prediction-targeted development evidence, not
an exhaustive independent event reference. Counts can still conceal
cancelling false and missed events.

The [boundary overview](china-same-colour-gap-overview.jpg) shows six end
changes between same-colour candidate pairs; the remaining end change is
visible at [4940 s](china-boundary-4940.jpg). The audit JSON records all seven
review times and the first and last candidate ID assigned to each end.
The [end-aware sequence audit](../../prototype/event_sequence_consistency.py)
uses those source-reviewed boundary times to report raw and reviewed
candidate counts without changing predictions. In the raw timeline, ends 6
and 7 each contain ten red candidates, two above the normal per-team
capacity. Same-colour adjacency flags three of the four source-reviewed
non-stone tracks; R01-S177 falls near an end boundary and needs the count
check. These constraints prioritize review but cannot choose which event to
remove or prove that an end is complete.

An [automatic 2024 end-marker probe](END-MARKER-TRANSFER.md) calibrates the
scoreboard's position and column spacing per video. It finds repeated display
states 1–8 on China, Estonia and Italy, then isolates three one-frame
backward misreads. This supplies end-order evidence without manual marker
annotation. The graphic can update after the next end's first throw, so its
change time is not used as a physical boundary or a throw timestamp.

A [separate 360p replay](2024-360P-REPLAY.md) of reviewed China and Estonia
windows reproduces the same two real-throw timestamps and three likely
false-event timestamps on newly downloaded video variants. The existing
confirmation stage accepts all five, so the next discriminator must address
physical object identity and delivery origin.

The [tracked-object patch transfer](IDENTITY-PATCH-TRANSFER.md) makes that
identity check concrete on 18 reviewed 2024 tracks. A China-trained linear
appearance model rejects the reviewed Estonia broom track, but also rejects
two of seven reviewed real Estonia stones. On a third, exact-source Italy
packet it retains only 2 of 17 tracks matched to earlier source-only delivery
windows. It is retained as diagnostic evidence, not added as a hard throw gate.

A [systematic China catalog](CHINA-CATALOG-REVIEW.md) replays all 131
provisional events and separates tracked-object identity from throw-event
identity. Four tracks visibly follow non-stones; a fifth merges a moving
person into a red stone near the event crossing. Rejecting that whole track
as non-stone would lose a source-supported delivery. Crossing-local patch
sampling improves some model scores but still misses reviewed real stones.

A [stationary-to-motion episode audit](MOTION-EPISODE-RESULTS.md) isolates the
moving segment of that merged track at 6876.1 s. The fixed diagnostic flags
only this case among 368 provisional 2024 events. It improves this event's
trajectory evidence without making an exact release-time or F1 claim.
