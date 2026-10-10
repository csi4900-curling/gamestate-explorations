# Pre-inference same-production holdout — 7 October 2026

Source: 2022 Paralympics Sweden–Switzerland, catalogue row 5,
https://www.youtube.com/watch?v=ZJAMdkERdpE. Chosen before download/viewing as a
different match that appears likely to use the Beijing 2022 production family.
Whether the scoreboard actually has the same layout must be determined from
the source; an unsupported layout is a coverage failure, not permission to
retune the model before its first score.

Fixed media interval: 1650–2760 seconds. Prepare a source-only event reference
from the recording and freeze it before opening model output. Do not tune the
Beijing scoreboard or final-stone visual fallback on this recording before the
first score. Do not ask the user to label it.

Frozen candidate and scorer fingerprints before source inspection:

- `prototype/broadcast_scoreboard.py`: `bd789d69bb6cd5f2b522c2bdf0ea7efad151ef0d265841c4be83fee7e5a3e747`
- `prototype/stone_motion_fallback.py`: `f8c16decfd1e761a327c8a160b8a759ed67c0b2261b25073c31ce5a0cbcbb007`
- `prototype/scripts/run_beijing_scoreboard.py`: `8b19a879d6c176ab45dc35f3d9061ab3f02829caf7dbf7d7d23978c6282e3f29`
- `prototype/throw_event_benchmark.py`: `f5a76cc3ea8b37ff13d90fc919f7192753276873b603ef01d4ef5b6f743307f6`

Use zero extra tolerance, `evidence_interval` matching with a maximum 35-second
prediction interval, and also report the stricter point-time score. Both are
development/agent-reference results; a single same-production match does not
certify cross-camera-family generalization.

Source-only reference frozen before inference as `blind-reference.json`, SHA-256
`60177f4efba0be4642577b03f98a76e7829fb420d702a94ca72b006d76bcbcfd`.
Downloaded source SHA-256:
`49429abdd3796e8240e66c201d37e94e71a7bb6225890b2492bea26d2f70d560`.
