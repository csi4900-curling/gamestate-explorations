# Latvia accepted-event gap at 4279–4726 s: source review

The frozen [Latvia full timeline](latvia24-full-v1/timeline.json) has no accepted
left event between `R01-S98` at 4279 s and `R01-S104` at 4726 s. That 447-second
interval is *not* 447 seconds of demonstrated missed throws. A reproducible
[20-second full-frame grid](../../canada-latvia-2024/left-event-gap-4279-4726-source-sheets/manifest.json)
shows players clearing the previous house, a long visually empty house, then
players and stones returning near the next start. It is a sampled source
review, not an exhaustive throw annotation or a verified physical end boundary.

The existing [raw decision artifact](latvia24-full-v1/run-02/events.json)
contains five unconfirmed motion proposals in this gap: `S99` and `S100` near
4300 s, plus `S101`–`S103` near 4585–4587 s. The latter three were rejected
as outside the left ice corridor. A denser [one-second left-camera source
grid](../../canada-latvia-2024/left-restart-4585-source-sheets/manifest.json)
shows an athlete rolling up the left side of the house while an attendant
handles and places a red stone near the centre. The apparent red/yellow motion
at x≈45 px follows the athlete/broom area, not a source-visible delivered-stone
transit across the left-panel ice. `S99`/`S100` occur during the clearing phase in the coarse
grid; sparse frames do not establish their object identities.

This prevents a tempting false rescue of `S101`–`S103` based only on their
timing near play resumption. It also means the large accepted-event time gap
cannot be translated directly into a number of missed shots. Later Latvia
left-camera silence from 5003 to 6716 s is different: the already preserved
[right-entry review tier](latvia24-full-v1/right-entry-review-triage.json)
contains eight short prefixes between 5066 and 5567 s, several with
source-visible moving-stone pixels. Those remain right-only review proposals
and do not establish a complete physical throw count, exact release or settle,
end identity, or simulation-ready state.
