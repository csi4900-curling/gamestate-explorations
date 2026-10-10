# Large-cap fallback development check

After the frozen learned-box screen missed the coarse yellow window at 395–445 s,
source frames showed a large moving yellow cap. A five-hertz multiscale cap
tracker recovered a yellow 413.0–430.2 s track in that already exposed window.
Red graphic/player tracks started earlier but jumped across the image. A
cap-only smooth-motion condition was chosen on this exposed 50-second window:
the longest uninterrupted run must last at least 2.0 s and contain at least
eight steps over 4 px; a run breaks at a jump over 25 px or a gap over 0.4 s.
The existing live-overlay, local-ice, and episode checks then apply. This is
postscore fitting, not transfer evidence.

Freeze this rule before a 300–600 s cap scan and any further source-only
positive interval. Screen with `--large-cap-fallback` and preserve both raw
and screened artifacts. Do not alter the frozen learned-box score. The next
positive source interval should be labelled from source-only sheets before
running this fallback. Independent test annotations remain unavailable.

- Screen model SHA-256: `9444fc2e38b0f2b4a2efa9a143aec2e8229ee814c2324a3001b179049e672909`
- Screen runner SHA-256: `7646970074d8961dcfc6ef56f1d021e7aca463761431eb2c2b2f5bd58c49414b`
- Cap runner SHA-256: `bef1b62e433d5417079782f39c6503a9632ac4959ac7cf736b61392d583bf161`

The full exposed 300–600 s cap scan yielded 3 screened candidates: the
missing yellow one and two wrong-colour duplicates of primary learned-box
events. Cap-only score was 3 TP, 0 FP, 4 FN temporally but just 1 colour-aware
TP. A frozen development fusion now keeps all primary candidates and adds a
screened cap candidate only if no primary event is within 20 seconds of its
crossing. This separation is fitted to 300–600 s and must be evaluated on the
already selected 600–885 s reference without further tuning.

- Fusion runner SHA-256: `ff73b44c53cbf6d256e6b95345d17516ad2070b0c700261da33c29b979b367dd`
