# Frozen weak-origin rescue transfer through a live/graphic interruption

Select Sweden–Switzerland 2022 interval **1800–2100 s**, fixed before
shot-level inference. A ten-second source check found the compact live
overlay in 21/30 frames, so this span includes non-live or unsupported
graphic periods as well as live play. It has not been used to fit the
shot-origin pair model or weak-origin rescue; the match itself is exposed.

- Source SHA-256: `49429abdd3796e8240e66c201d37e94e71a7bb6225890b2492bea26d2f70d560`
- Frozen origin model SHA-256: `9586973ae7cbc632c65e3b757015f30d1d2fcf38190d50c39bb43c4ed827661a`
- Two-shot rule SHA-256: `4ed5732d5140e5bc972898c794b1e89388a31243a7bdda0a21e48845663df129`
- Weak-origin rescue SHA-256: `807522370bab7dd4f27b2ad21f36e3bc15fdbc2fcb8b1db02c6467c5f561bddf`

Freeze source-only shot labels before running predictions. Apply the
origin model at probability ≥0.5 with its current-or-next live-overlay
condition, then adjacent-shot same-colour motion from either cap or learned
boxes. The predeclared rescue allows probability ≥0.2 only when both
channels support exactly one shared colour and at least one channel's
support is unique. Report all unresolved labels and preserve the first
score unchanged. This is development transfer, not independent full-video
throw-event F1.
