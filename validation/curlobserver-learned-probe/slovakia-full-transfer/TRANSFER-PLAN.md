# Frozen full-recording Slovakia–USA 2022 transfer

The source is the already exposed Slovakia–USA Paralympics 2022 recording
(`Ns12UZ5nlPk`, 0–7616 s, SHA-256
`eba1d86944a2f4278b6e5e2c7549d12b47e5e8a51bf0c680b2db372c6ec12420`).
One 300-second interval from this match supplied development labels, but
the remaining full recording has not been reviewed shot by shot. This
is a cross-match **development transfer**, not independent validation.

Before inspecting the full-match predictions, the shot-origin model is
fixed to `shot-origin-pair-v1/model-excluding-slovakia-dev.npz` (SHA-256
`c11270b3f3681c7b3eb5579c2132cdaf8c7c08b0807558b93443a32c7e48d7d2`).
It was fitted without Slovakia shot labels. The same 5 Hz hard-cut scan,
three-frame shot inference, within-shot cap tracking, selected learned-box
channel, counter association, immediate-following-motion rescue,
existing-visual conflict link, travel-only fallback and event-ledger
rules used on the full China source will be applied without threshold
changes. The current association, fusion, travel and ledger code hashes
are `4f4ac237`, `ce7d786e`, `32d37ea3` and `8bda5303` respectively
(full hashes in their outputs).

The first report will preserve the raw and replayed counter changes,
unreadable seconds, shot and candidate counts, one-to-one counter
association, travel-only candidates, visual-only candidates, colour
conflicts and counter-state discontinuities. Counter concordance is a
coverage proxy, not throw precision, recall or F1. No full-video event
accuracy claim follows without independent exhaustive event labels.
