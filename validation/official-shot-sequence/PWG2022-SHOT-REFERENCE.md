# Independent 2022 Paralympic shot-order reference

The official [Beijing 2022 wheelchair curling results book](https://curlit.com/PDF/PWG2022_ResultsBook.pdf)
contains shot-by-shot pages for the three session-one recordings already used
in the project. The [extractor](../../prototype/scripts/extract_pwg2022_shot_ledger.py)
parses each numbered delivery, team, shooter, shot type, evaluation, rotation
and notes into a [source-hashed ledger](pwg2022-official-shot-ledger.json).
It also reads the coloured team icons on every shot page: Switzerland,
China and Slovakia use red handles; Sweden, Canada and USA use yellow.
The PDF and exact video hashes, result-page numbers and shot-page numbers
are in that ledger. These official records were produced independently of
the video detector.

| Recording | Official game code | Result PDF page | Shot PDF pages | Official shots | Full-video candidates | Difference |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| Sweden–Switzerland | PREL000101 | 535 | 536–542 | 112 | 121 | +9 |
| Canada–China | PREL000102 | 543 | 544–551 | 125 | 133 | +8 |
| Slovakia–USA | PREL000103 | 552 | 553–559 | 112 | 119 | +7 |

The [candidate count audit](pwg2022-candidate-count-audit.json) checks that
each development ledger's video hash matches the official ledger's linked
recording. Canada–China's last end has **13** numbered official deliveries
and is marked unfinished due to concession. The other seven Canada–China
ends and all recorded ends in the other two games have 16 numbered shots.
Using eight complete ends as a fixed 128-shot target would be wrong for the
China game.

The official pages supply **order and post-shot diagrams, not video times**.
The [board-state extraction](PWG2022-BOARD-STATE.md) now recovers approximate
unitless stone positions from those diagrams, with edge and low-fill
uncertainty flags. Count excess does not identify which candidate is extra: misses,
wrong colours, duplicate detections, off-play detections and uncovered source
intervals can coexist. The count audit is therefore a constraint on a future
timestamped reference and detector, **not a measured full-video F1**. The
existing candidate ledgers were development outputs, not previously frozen
predictions against this newly extracted official reference.

The next useful alignment is official shot index ↔ video delivery window,
using source-video evidence and the 2022 remaining-stone graphic while
preserving ambiguity at unreadable counters and camera cuts. Once aligned,
the official post-shot states can test video board reconstruction without
assuming the detector's predicted stone positions are correct.

The [official-counter alignment](pwg2022-official-counter-alignment.json)
now maps unique, colour-consistent graphic decrements to official shot IDs.
When a slot has several reads, it also retains the one matching official
handle colour if that match is unique; same-colour duplicates remain
ambiguous. The counter supplies a delayed broadcast observation,
**not a release timestamp**. Candidate links to this counter are also
development evidence, since the candidate builder already used the graphic.

| Game | Unique colour-consistent counter slots | Ambiguous or conflicting counter reads | Candidate links with proposed release after linked counter update |
| --- | ---: | ---: | ---: |
| Sweden–Switzerland | 95 / 112 official shots | 8 | 0 |
| Canada–China | 114 / 125 | 2 | 0 |
| Slovakia–USA | 91 / 112 | 7 | 0 |

The audit verifies that each candidate ledger's recorded counter-input hash
matches the counter replay used here. Earlier raw counter scans have different
event IDs and must not be paired with these candidates. A preliminary
comparison with those raw scans created a false Canada–China time-order
failure; it disappeared with the provenance-matched replay. The current
[candidate ledger builder](../../prototype/throw_event_ledger.py) now rejects
a counter link whose update precedes its candidate's proposed release window.

The [gap review packet](pwg2022-official-gap-review.json) lists all 49
official shots without a clean counter anchor (17 Sweden–Switzerland, 11
Canada–China, 21 Slovakia–USA). Fifteen gap runs, covering 17 shots, have
counter observations on both sides and therefore a bounded video search
span. Four have one visual-only candidate with matching colour, seven have one
with unknown colour, one has a colour conflict, one spans multiple candidates,
and two have no visual-only candidate. These are **review priorities**, not
recovered ground-truth timestamps or detector true/false positive counts.

The [video motion probe](pwg2022-bounded-gap-motion-probe.json) samples the 12
bounded, single-shot gaps that have exactly one visual-only candidate. It
records strict cap tracks at 0.2 and 1 second sampling, and a relaxed
large-cap channel at 0.2 seconds. Every targeted gap has at least one track in
one channel, but neither channel alone covers all 12. The same fixed probe on
four previously exposed nonthrow windows (both colours) produces a spurious
red track in the 8220–8250-second post-game window. Thus **motion alone cannot
confirm a throw**, and these selected windows cannot measure full-video
recall or precision. Source inspection illustrates the camera-view challenge:
Slovakia–USA end 2 shot 4 shows a yellow stone around 1286 seconds even though
the candidate says red; end 4 shot 14 shows a red delivery at 3872 seconds and
a red stone on the ice at 3888 seconds. The 1-second tracker misses the latter,
while the 0.2-second tracker finds motion only after the cut. It does not prove
that the two views contain the same physical stone. The next detector step
needs continuity evidence across those views and camera-motion rejection.

The [post-cut colour audit](pwg2022-postcut-colour-audit.json) tests a frozen
visual-only rule: after a verified edit, look for sustained cap motion in the
receiving view, reject tracks whose displacement is fully explained by a
reliable camera transform, and choose a colour only when one remains. On the
12 selected gap cases it chooses 10 colours matching the official record and
abstains twice. Without the camera check it incorrectly chose red for
Canada–China end 6 shot 13; those red tracks were stationary stones moving in
the camera view, while the official shot was yellow.

A [broader transfer audit](pwg2022-postcut-colour-transfer.json) uses the same
rule on 24 evenly spaced counter-anchored origin candidates per match that
were outside the 12 gap cases. It resolves 22/24 Sweden–Switzerland, 17/24
Canada–China and 19/24 Slovakia–USA colours, all 58 matching the official
handle colour, with 14 abstentions. This sample is still from the same three
development recordings and selects candidates that already have clean counter
links. It tests post-cut colour support, **not** throw-event precision, recall,
release time, or independent cross-recording F1.

The [source-only colour sidecar](pwg2022-visual-only-postcut-colours.json)
then applies that rule to **all 64 visual-only origin candidates** in the three
development ledgers, without looking up any official shot IDs or colours.
It resolves 45 colours and abstains on 19. Among resolved cases, 18 had been
unknown in the ledger and eight conflict with its original colour; all eight
change red to yellow. The original ledger is preserved.

A separate [official sequence audit](pwg2022-official-candidate-sequence-audit.json)
uses the published shot order and clean counter anchors to inspect candidate
chronology. Its baseline alignment has 328 candidate/shot pairings that are
the same across all lowest-cost alignments under the stated edit costs; 30
candidates are skipped under that model and 15 have ambiguous placements.
Substituting only the source-only post-cut colours yields 332 stable pairings,
27 skipped candidates and 14 ambiguous candidates in the
[augmented audit](pwg2022-official-candidate-sequence-postcut-audit.json).
For example, Slovakia–USA candidate T021 moves from model-skipped to the
official end 2 shot 4 after its colour changes from red to yellow. This
demonstrates why a model-skipped candidate cannot simply be counted as a
false positive. The alignment reads official order, uses a chosen edit cost,
and lacks independent video throw timestamps; none of these figures is F1.

The [duplicate-evidence fusion audit](pwg2022-candidate-duplicate-fusion.json)
applies a source-only containment rule to all 373 development candidates:
group a visual-only release window into exactly one counter-backed release
window when it is wholly contained and colours do not conflict. It groups
two Sweden–Switzerland candidates (`T080`, `T081`) under counter-backed
`T082`, yielding 371 provisional event groups while retaining every raw
candidate ID. Both grouped candidates were skipped by the separate official
sequence cost model; source frames show player preparation at 4768–4789 s
and the red stone later in transit around 4796 s. The unchanged rule groups
none in the other two recordings. This is a narrow duplication proposal,
not proof that every remaining candidate is a throw or that the grouped
candidates are false. Broad counter-backed windows could cover adjacent
real throws, so independent timing evaluation is still needed before using
this rule as a hard production suppression.

### Visual-only counter proxy on complete ends

The [visual-to-counter proxy audit](pwg2022-visual-counter-proxy.json)
separates the pre-counter cap-motion confirmation stage from the delayed
broadcast counter. Only two official ends have all 16 shots paired to clean,
colour-concordant counter updates: Canada–China end 4 and Slovakia–USA end 3.
A monotone one-to-one match within fixed timing limits pairs 13/16 visual
candidates in the China end and 16/16 in the Slovakia end, with no unmatched
visual candidates in either bounded interval. The China misses are official
end 4 shots 9, 12 and 13. All three have a positive origin-view prediction
but fail the original cap-only adjacent-motion confirmation. This is a
**delayed-counter agreement diagnostic**, not independent event F1: broad
shot intervals can match the wrong nearby update, and 20 other 2022 ends
do not have complete counter coverage.

The [post-cut rescue audit](pwg2022-postcut-proxy-rescue.json) applies the
previously developed camera-filtered receiving-view cap-motion rule to all
four origin-positive but cap-unconfirmed windows in those two complete ends.
It resolves China shot 9's red motion, abstains on shots 12 and 13 and one
nearby unconfirmed origin, and raises proxy matches from 29/32 to 30/32
without adding an unmatched candidate. Source frames show the missed red
and yellow deliveries across camera edits, but this remains an in-sample
development result. Neither the post-cut cue nor the counter proves that
the stone before and after an edit is the same physical object.

An [early origin-view release cue](../../prototype/origin_release_passage.py)
looks for a coloured cap held near the delivery-side ice for at least one
second, then moving at least 35 pixels within 1.6 seconds before the cut.
Its first [three-recording transfer](pwg2022-origin-release-transfer.json)
scanned all 74 origin-positive, cap-unconfirmed shot windows and found six
unique passages. Two are the remaining China end-4 misses. One Swiss passage
was **false**: red clothing moved against a white uniform with no stone in
that view. The preserved failure led to a [postscore ice-context gate](pwg2022-origin-release-ice-gate.json)
that requires a broad white-ice region below the held cap. It keeps five
passages and rejects that clothing case. This is development tuning on the
same recordings, not an independent false-positive rate.

The [combined visual proxy audit](pwg2022-combined-visual-counter-proxy.json)
adds the ice-gated passage cue only where cap confirmation and post-cut
motion abstained. On the two complete counter-anchored ends, matches rise
from 29/32 (cap-only) to 30/32 (post-cut) to **32/32** (combined), with 32
visual candidates. This is an **in-sample ceiling**: the passage rule was
created from those China misses and the ice gate from a transfer false
positive. It does not establish independent throw precision, recall,
generalization to another camera layout, or accurate physical release times.
