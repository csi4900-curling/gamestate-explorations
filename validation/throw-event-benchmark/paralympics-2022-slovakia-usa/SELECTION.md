# Pre-inference same-production transfer — 7 October 2026

Source: 2022 Paralympics Slovakia–USA, catalogue row 6,
https://www.youtube.com/watch?v=Ns12UZ5nlPk. Selected before downloading or
viewing this recording. The detector has already been developed against the
Canada–China and Sweden–Switzerland Beijing broadcasts; this is an untouched
match check of the revised candidate, not cross-production validation.

Fixed media interval: 1650–2760 seconds. Prepare source-only delivery windows
from five-second contact sheets and freeze the reference before inference. Keep
the first score unchanged even if the graphic or camera differs. Do not request
manual labels from the user.

Frozen candidate fingerprints before source inspection:

- `prototype/broadcast_scoreboard.py`: `bd789d69bb6cd5f2b522c2bdf0ea7efad151ef0d265841c4be83fee7e5a3e747`
- `prototype/stone_motion_fallback.py`: `c6ebacf8c46e50b08f5ab02ee4a206fec6e247d35393ad7439be3b21bf4a3522`
- `prototype/scripts/run_beijing_scoreboard.py`: `2a2bddcba46af0c172c5eff96b9cb16e4445fe4f3fa43f3c299eb487a7d45554`
- `prototype/throw_event_benchmark.py`: `f5a76cc3ea8b37ff13d90fc919f7192753276873b603ef01d4ef5b6f743307f6`

Score with zero extra tolerance and bounded evidence intervals (maximum 35 s),
and report the stricter point-time score separately. Agent-blind coarse windows
are useful for development but cannot independently establish high F1.
