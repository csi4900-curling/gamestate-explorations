# Painted-house alignment transfer to Czechia 2024

The Latvia development guard was replayed unchanged against the full Canada–Czechia 2024 right-entry ledger. The [source-hashed export](right-entry-transfer/czech-full-house-alignment-transfer.json) samples the 640×360 source **20 seconds after each of 45 provisional right-entry crossings**, extracts blue paint in the same fixed house crop, and checks the 44 adjacent sample pairs for a zero-pixel best translation and mask overlap of at least 0.7.

**34 of 44 pairs pass; ten abstain.** This is a transfer diagnostic for whether two selected images support raw pixel comparison. It is neither an event accuracy result nor a stone-state accuracy result. Entries are detector proposals, and adjacent proposals can straddle an end, a broadcast phase, or a long gap.

| Abstaining pair | Best shift (px) | Blue-mask overlap |
| --- | ---: | ---: |
| R025–R028 | −1, 0 | 0.427 |
| R028–R094 | +1, 0 | 0.480 |
| R114–R121 | 0, 0 | 0.569 |
| R121–R126 | 0, 0 | 0.566 |
| R132–R136 | +2, 0 | 0.350 |
| R136–R140 | −2, 0 | 0.366 |
| R194–R195 | +1, 0 | 0.569 |
| R195–R197 | 0, 0 | 0.625 |
| R197–R199 | 0, 0 | 0.675 |
| R219–R265 | 0, 0 | 0.526 |

The [rejected source-frame pairs](right-entry-transfer/czech-full-house-alignment-rejections.jpg) show that players, wheelchairs and stones obscure varying portions of the blue ring. The low scores therefore cannot be interpreted as ten camera moves; the mask is an abstention cue, not a camera-motion classifier. Conversely, a passing pair verifies neither a full camera transform nor stable pose between its two sampled instants. No physical stone identity, end identity, or simulation parameter follows from this audit.

Reproduce with [the transfer script](../../../../prototype/scripts/audit_right_entry_house_transfer.py), the full Czech `source-360p.mp4`, and the [45-entry variant ledger](right-entry-transfer/czech-full-0-6683-variant-235-225.json), writing to an unused output path. The 0.7 cutoff was chosen on exposed Latvia footage before this Czech replay; the same Czech footage had already been used for detector development, so this is not independent validation. A more robust board comparator will need to register static paint while masking moving foreground and explicitly detect scene cuts or new camera poses.
