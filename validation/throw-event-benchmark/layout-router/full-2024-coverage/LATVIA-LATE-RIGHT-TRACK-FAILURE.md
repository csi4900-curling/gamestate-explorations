# Latvia late static-left interval: why a looser right-entry line is unsafe

The frozen [Latvia right-entry tier](latvia24-full-v1/right-entry-review-triage.json)
surfaces eight review prefixes at source times 5066–5567 s, but no further
prefixes before the left camera resumes around 6670 s. The official [results
book](../../../official-shot-sequence/WWhCC2024_ResultsBook.pdf) reports six
completed ends and a final Latvia 2–Canada 9. Around 5800 s, the source
scoreboard still displays Latvia 2–Canada 7, the score after five ends. This
context shows that late-match play and score progression require investigation;
it does **not** timestamp the sixth end's throws.

The existing 1 Hz [right-colour raw probe](latvia24-full-v1/right-motion-in-static-left.json)
retains ten yellow tracks starting at or after 5600 s. Their reproducible
[first/middle/last source strips](../../canada-latvia-2024/right-late-yellow-track-source-sheets/manifest.json)
mostly show a marked cap near an athlete, an occluded/parked stone, or a stone
being handled. They do not establish a clear delivered-stone passage in the
sampled frames. In particular, a cap shifts from about `(411,205)` to
`(482,209)` between 5802 and 5805 s. The denser [right-camera source grid](../../canada-latvia-2024/right-handled-yellow-5800-source-sheets/manifest.json)
shows an attendant pushing that yellow stone with a broom, so a simple
horizontal-motion rescue would generate a false throw proposal here.

This is a **failure diagnosis of the current proposal lane**, not proof that
the sixth end is unobservable or that all ten tracks are nonthrows. Three
stills per track can miss a physical transit between samples; the cap detector
can lose a moving stone behind players, and the broadcast may change the
useful direction or camera. The next right-view detector needs a source-tested
stone/object identity cue, handling-vs-delivery context, and an explicit
camera-direction state before attempting to fill this interval. The local
[model-v2](../../../curlobserver-learned-probe/model-v2/results.json) is a
176-feature patch classifier inside a full-frame colour-proposal pipeline.
A [postreview eight-frame transfer](../../canada-latvia-2024/late-right-stone-box-selected-development.json)
tests it alongside the existing v1 and public-tracking-v2 box models: v1/v2
return right-ROI boxes on 2/8 selected frames, and public-tracking-v2 on 5/8.
The public model also boxes the broom-handled yellow stone at 5805 s. These
selected-frame counts are neither box recall nor throw accuracy; simply
swapping the classifier does not distinguish delivery from handling.
The eight
earlier right-only entries and all original left candidates remain unchanged;
no full-match throw recall, physical end assignment, or simulation-ready game
state is claimed.
